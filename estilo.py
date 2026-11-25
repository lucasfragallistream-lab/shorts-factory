"""Shared paper-cutout drawing helpers.

All drawing coordinates are given at 1x (final) scale; `Pincel` multiplies them by
config.SUPERSAMPLING so shapes are drawn at 2x and later reduced with LANCZOS.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import config

SS = config.SUPERSAMPLING
CONTORNO = (34, 26, 30, 255)
LARGURA_CONTORNO = 3


def s(v: float) -> int:
    return round(v * SS)


def pts(seq) -> list[tuple[int, int]]:
    return [(s(x), s(y)) for x, y in seq]


def caixa(b) -> list[int]:
    return [s(v) for v in b]


_FONTES_SISTEMA = ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


@lru_cache(maxsize=32)
def fonte(tamanho: int) -> ImageFont.FreeTypeFont:
    """Bold font with Portuguese accents: assets/fonts/*.ttf first, then system fonts."""
    candidatos = sorted(config.FONTES.glob("*.ttf")) + [Path(f) for f in _FONTES_SISTEMA]
    for c in candidatos:
        if c.exists():
            return ImageFont.truetype(str(c), tamanho)
    return ImageFont.load_default(size=tamanho)


_FONTES_BLACK = ("C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/impact.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


@lru_cache(maxsize=64)
def fonte_black(tamanho: int) -> ImageFont.FreeTypeFont:
    """Heaviest available font for captions: assets/fonts/legenda.ttf, then system black fonts."""
    for c in [config.FONTES / "legenda.ttf"] + [Path(f) for f in _FONTES_BLACK]:
        if c.exists():
            return ImageFont.truetype(str(c), tamanho)
    return fonte(tamanho)


def _cor(c):
    if c is None:
        return None
    c = tuple(int(v) for v in c)
    return c + (255,) if len(c) == 3 else c


def arco_pts(cx, cy, a, b, t0, t1, n=24) -> list[tuple[float, float]]:
    """Points along an ellipse from angle t0 to t1 (degrees, clockwise from 3 o'clock)."""
    out = []
    for i in range(n + 1):
        t = math.radians(t0 + (t1 - t0) * i / n)
        out.append((cx + a * math.cos(t), cy + b * math.sin(t)))
    return out


def nova_camada(largura: int, altura: int) -> Image.Image:
    """Transparent supersampled layer for a 1x size."""
    return Image.new("RGBA", (s(largura), s(altura)), (0, 0, 0, 0))


def reduzir(img: Image.Image, largura: int, altura: int) -> Image.Image:
    return img.resize((largura, altura), Image.Resampling.LANCZOS)


def mascara(img: Image.Image, forma: str, geom) -> Image.Image:
    """L mask with a filled 'elipse' or 'poligono' (1x coordinates)."""
    m = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(m)
    if forma == "elipse":
        d.ellipse(caixa(geom), fill=255)
    else:
        d.polygon(pts(geom), fill=255)
    return m


def recortar(camada: Image.Image, m: Image.Image) -> Image.Image:
    """Keep only the part of `camada` inside mask `m`."""
    camada.putalpha(ImageChops.multiply(camada.getchannel("A"), m))
    return camada


class Pincel:
    """ImageDraw wrapper: 1x coordinates in, supersampled pixels out, dark outline by default."""

    def __init__(self, img: Image.Image, largura_padrao: float = LARGURA_CONTORNO):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.lp = largura_padrao

    def _w(self, largura):
        return max(1, s(self.lp if largura is None else largura))

    def elipse(self, b, cor, contorno=CONTORNO, largura=None):
        self.d.ellipse(caixa(b), fill=_cor(cor), outline=_cor(contorno), width=self._w(largura))

    def poligono(self, p, cor, contorno=CONTORNO, largura=None):
        self.d.polygon(pts(p), fill=_cor(cor), outline=_cor(contorno), width=self._w(largura))

    def retangulo(self, b, cor, contorno=CONTORNO, largura=None, raio=0):
        if raio:
            self.d.rounded_rectangle(caixa(b), radius=s(raio), fill=_cor(cor), outline=_cor(contorno),
                                     width=self._w(largura))
        else:
            self.d.rectangle(caixa(b), fill=_cor(cor), outline=_cor(contorno), width=self._w(largura))

    def linha(self, p, cor=CONTORNO, largura=None, arredondada=True):
        w = self._w(largura)
        self.d.line(pts(p), fill=_cor(cor), width=w, joint="curve")
        if arredondada:
            r = w / 2
            for x, y in (p[0], p[-1]):
                self.d.ellipse([s(x) - r, s(y) - r, s(x) + r, s(y) + r], fill=_cor(cor))

    def arco(self, b, ini, fim, cor=CONTORNO, largura=None):
        self.d.arc(caixa(b), ini, fim, fill=_cor(cor), width=self._w(largura))

    def corda(self, b, ini, fim, cor, contorno=None, largura=None):
        self.d.chord(caixa(b), ini, fim, fill=_cor(cor), outline=_cor(contorno), width=self._w(largura))

    def texto(self, xy, txt, tamanho, cor, anchor="mm"):
        self.d.text((s(xy[0]), s(xy[1])), txt, fill=_cor(cor), font=fonte(s(tamanho)), anchor=anchor)


@lru_cache(maxsize=8)
def _ruido(largura: int, altura: int, intensidade: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    fino = rng.normal(0.0, 1.0, (altura, largura)).astype(np.float32)
    g = rng.normal(0.0, 1.0, (max(altura // 20, 2), max(largura // 20, 2))).astype(np.float32)
    grosso = np.asarray(Image.fromarray(g, "F").resize((largura, altura), Image.Resampling.BICUBIC))
    return 1.0 + intensidade * (0.6 * fino + 0.5 * grosso)


def textura_papel(img: Image.Image, intensidade: float = 0.025, seed: int = 7) -> Image.Image:
    """Multiply RGB by fixed fibrous noise (alpha untouched)."""
    arr = np.asarray(img).astype(np.float32)
    arr[..., :3] *= _ruido(img.width, img.height, intensidade, seed)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), img.mode)


def sombra_recorte(img: Image.Image, desloc=(5, 7), opacidade: float = 0.38, desfoque: float = 2.0) -> Image.Image:
    """Soft drop shadow under an RGBA cutout, same canvas size."""
    sombra = Image.new("RGBA", img.size, (20, 14, 18, 0))
    sombra.putalpha(img.getchannel("A").point(lambda v: int(v * opacidade)))
    base = Image.new("RGBA", img.size, (20, 14, 18, 0))
    base.paste(sombra, desloc)
    base = base.filter(ImageFilter.GaussianBlur(desfoque))
    return Image.alpha_composite(base, img)
