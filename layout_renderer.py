"""Ranking layout in the style of docs/referencia_estilo.png.

Frame zones (1080x1920):
    title banner (red, tilted)  ~ y 150..420
    stage (stairs + figures + tags)  y PALCO_Y0..PALCO_Y1
    big yellow label of the current item  y ROTULO_Y
    captions  centered at LEGENDA_Y (above the 380 px bottom reserve)

`Palco` draws only the stage band, at any scale, so the R4 camera can zoom into an item by
cropping a larger render instead of upscaling pixels. Title and yellow label are fixed overlays.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from PIL import Image, ImageDraw

import config
import figure_renderer as fr
from estilo import fonte, fonte_black
from schemas import Ranking

L, A = config.LARGURA, config.ALTURA
SS = config.SUPERSAMPLING

FUNDO = (252, 252, 250)
TRACO = (38, 40, 50)
VERMELHO = (230, 70, 64)
SOMBRA = (38, 40, 50)
AZUL_TAG = (126, 184, 238)
AMARELO = (255, 214, 10)
DEGRAU = (255, 255, 255)
DEGRAU_LADO = (232, 234, 238)

TITULO_Y = 268
PALCO_Y0, PALCO_Y1 = 430, 1275
CHAO_Y = 1245  # bottom line of the stairs
MARGEM_X = 64
ROTULO_Y = 1310
LEGENDA_Y = 1465

_ALTURA_FIG = {3: 540, 4: 500, 5: 430}
_DEGRAU_H = {3: 80, 4: 58, 5: 46}


# --- text helpers ------------------------------------------------------------
def _quebrar(texto: str, fnt, largura_max: int) -> list[str]:
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = f"{atual} {p}".strip()
        if fnt.getlength(teste) <= largura_max or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _texto_contorno(d: ImageDraw.ImageDraw, xy, txt, fnt, cor, contorno, w, anchor="mm"):
    d.text(xy, txt, font=fnt, fill=cor, stroke_width=w, stroke_fill=contorno, anchor=anchor)


# --- title banner --------------------------------------------------------------
@lru_cache(maxsize=16)
def camada_titulo(titulo: str) -> Image.Image:
    """Red tilted banner with white heavy text, as a full-width RGBA layer (paste at y = TITULO_Y - h/2)."""
    larg_max = 880
    for tam in range(84, 40, -4):
        fnt = fonte_black(tam * SS)
        linhas = _quebrar(titulo.upper(), fnt, larg_max * SS)
        if len(linhas) <= 2 and max(fnt.getlength(x) for x in linhas) <= larg_max * SS:
            break
    asc, desc = fnt.getmetrics()
    lh = (asc + desc) * 0.92
    tw = max(fnt.getlength(x) for x in linhas)
    pad_x, pad_y = 44 * SS, 26 * SS
    bw, bh = tw + 2 * pad_x, lh * len(linhas) + 2 * pad_y
    sombra = 14 * SS
    img = Image.new("RGBA", (int(bw + sombra + 40 * SS), int(bh + sombra + 40 * SS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0 = 20 * SS, 20 * SS
    d.rounded_rectangle([x0 + sombra, y0 + sombra, x0 + bw + sombra, y0 + bh + sombra], radius=22 * SS, fill=SOMBRA)
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=22 * SS, fill=VERMELHO, outline=TRACO, width=6 * SS)
    d.rounded_rectangle([x0 + 10 * SS, y0 + 10 * SS, x0 + bw - 10 * SS, y0 + bh - 10 * SS], radius=16 * SS,
                        outline=(255, 140, 130), width=3 * SS)
    for i, ln in enumerate(linhas):
        cy = y0 + pad_y + lh * (i + 0.5)
        _texto_contorno(d, (x0 + bw / 2, cy), ln, fnt, (255, 255, 255), TRACO, 7 * SS)
    img = img.rotate(3, resample=Image.Resampling.BICUBIC, expand=True)
    img = img.resize((img.width // SS, img.height // SS), Image.Resampling.LANCZOS)
    camada = Image.new("RGBA", (L, img.height), (0, 0, 0, 0))
    camada.alpha_composite(img, ((L - img.width) // 2, 0))
    return camada


def desenhar_titulo(quadro: Image.Image, titulo: str, dy: float = 0.0) -> None:
    c = camada_titulo(titulo)
    quadro.paste(c, (0, int(TITULO_Y - c.height / 2 + dy)), c)


# --- tags and yellow label -------------------------------------------------------
def _texto_tag(rotulo: str, largura_max: float) -> tuple[list[str], int]:
    """Tag text that fits `largura_max`: full label, smaller, two lines, or just the first word."""
    for tam in range(36, 23, -2):
        fnt = fonte(tam)
        if fnt.getlength(rotulo) <= largura_max:
            return [rotulo], tam
    for tam in range(30, 21, -2):
        linhas = _quebrar(rotulo, fonte(tam), int(largura_max))
        if len(linhas) <= 2 and all(fonte(tam).getlength(x) <= largura_max for x in linhas):
            return linhas, tam
    return [rotulo.split()[0]], 30


@lru_cache(maxsize=128)
def tag(rotulo: str, atual: bool, largura_max: int, escala: float = 1.0) -> Image.Image:
    """Label tag with a pointer at the bottom center, RGBA, at `escala`."""
    linhas, tam = _texto_tag(rotulo, largura_max - 28)
    k = escala * SS
    fnt = fonte(round(tam * k))
    lh = fnt.getmetrics()[0] + fnt.getmetrics()[1]
    tw = max(fnt.getlength(x) for x in linhas)
    pad_x, pad_y, ponta = 14 * k, 8 * k, 12 * k
    w, h = tw + 2 * pad_x, lh * len(linhas) * 0.95 + 2 * pad_y
    img = Image.new("RGBA", (int(w + 8 * k), int(h + ponta + 8 * k)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0 = 4 * k, 4 * k
    cor = AZUL_TAG if atual else (255, 255, 255)
    lw = max(1, round(4 * k))
    cx = x0 + w / 2
    d.polygon([(cx - ponta, y0 + h - lw), (cx + ponta, y0 + h - lw), (cx, y0 + h + ponta)], fill=cor, outline=TRACO,
              width=lw)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=10 * k, fill=cor, outline=TRACO, width=lw)
    d.polygon([(cx - ponta + lw * 1.2, y0 + h - lw * 1.5), (cx + ponta - lw * 1.2, y0 + h - lw * 1.5),
               (cx, y0 + h + ponta - lw * 1.8)], fill=cor)
    for i, ln in enumerate(linhas):
        d.text((cx, y0 + pad_y + lh * 0.95 * (i + 0.5)), ln, font=fnt, fill=TRACO, anchor="mm")
    return img.resize((max(1, round(img.width / SS)), max(1, round(img.height / SS))), Image.Resampling.LANCZOS)


@lru_cache(maxsize=64)
def camada_rotulo(texto: str) -> Image.Image:
    """Big yellow label of the current item (full width RGBA, centered on ROTULO_Y)."""
    larg = L - 2 * 90
    for tam in range(92, 38, -4):  # always one line: two lines would run into the captions
        fnt = fonte_black(tam * SS)
        if fnt.getlength(texto) <= larg * SS:
            break
    linhas = [texto]
    lh = sum(fnt.getmetrics()) * 0.9
    img = Image.new("RGBA", (L * SS, int(lh * len(linhas) + 40 * SS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(linhas):
        y = 20 * SS + lh * (i + 0.5)
        d.text((L * SS / 2 + 6 * SS, y + 7 * SS), ln, font=fnt, fill=TRACO, stroke_width=9 * SS, stroke_fill=TRACO,
               anchor="mm")
        _texto_contorno(d, (L * SS / 2, y), ln, fnt, AMARELO, TRACO, 9 * SS)
    return img.resize((L, img.height // SS), Image.Resampling.LANCZOS)


def desenhar_rotulo(quadro: Image.Image, texto: str, escala: float = 1.0, alpha: float = 1.0) -> None:
    c = camada_rotulo(texto)
    if escala != 1.0:
        c = c.resize((max(1, round(c.width * escala)), max(1, round(c.height * escala))), Image.Resampling.BILINEAR)
    if alpha < 1.0:
        c = c.copy()
        c.putalpha(c.getchannel("A").point(lambda v: int(v * alpha)))
    quadro.paste(c, (int((L - c.width) / 2), int(ROTULO_Y - c.height / 2)), c)


# --- stage ---------------------------------------------------------------------
@dataclass
class EstadoFigura:
    expressao: str | None = None
    boca: str = "fechada"
    piscando: bool = False
    dy: float = 0.0  # vertical offset in frame px (bounce)
    esticar: float = 1.0  # squash & stretch (vertical scale)
    opacidade: float = 1.0  # < 1 fades the figure into the background (not the narrated item)


@dataclass
class Posicao:
    x: float  # center x, frame px
    chao: float  # feet y, frame px
    altura: int  # figure canvas height, frame px
    topo_cabeca: float = 0.0
    caixa: tuple[float, float, float, float] = field(default=(0, 0, 0, 0))  # figure + tag, frame px


class Palco:
    """Stairs, figures and tags of one ranking, drawn in the stage band at `escala`."""

    def __init__(self, ranking: Ranking, escala: float = 1.0):
        self.r = ranking
        self.n = len(ranking.itens)
        self.escala = escala
        self.largura = round(L * escala)
        self.altura = round((PALCO_Y1 - PALCO_Y0) * escala)
        self.sw = (L - 2 * MARGEM_X) / self.n
        self.posicoes = self._calcular()
        self.fundo = self._desenhar_degraus()

    # frame px -> stage px
    def _k(self, v: float) -> float:
        return v * self.escala

    def _y(self, y: float) -> float:
        return (y - PALCO_Y0) * self.escala

    def _alturas_degraus(self) -> list[float]:
        dh = _DEGRAU_H.get(self.n, 60)
        if self.r.layout == "fila":
            return [40.0] * self.n
        return [40.0 + i * dh for i in range(self.n)]

    def _calcular(self) -> list[Posicao]:
        alt = _ALTURA_FIG.get(self.n, 440)
        out = []
        for i, (it, h) in enumerate(zip(self.r.itens, self._alturas_degraus())):
            x = MARGEM_X + self.sw * (i + 0.5)
            chao = CHAO_Y - h
            pe = chao - alt * (fr.CHAO_U / fr.ALT_U)  # canvas top
            topo = pe + alt * fr.topo(it.personagem)
            larg_fig = alt * fr.proporcao() * 0.6
            out.append(Posicao(x, chao, alt, topo, (x - max(larg_fig, self.sw) / 2, topo - 90,
                                                   x + max(larg_fig, self.sw) / 2, chao + 10)))
        return out

    def _desenhar_degraus(self) -> Image.Image:
        k = self.escala * SS
        img = Image.new("RGB", (round(self.largura * SS), round(self.altura * SS)), FUNDO)
        d = ImageDraw.Draw(img)
        yb = (CHAO_Y - PALCO_Y0) * k
        x0 = (MARGEM_X - 20) * k
        lw = max(1, round(5 * k))
        hs = self._alturas_degraus()
        pts = [(x0, yb)]
        for i, h in enumerate(hs):
            xa = (MARGEM_X + self.sw * i - (20 if i == 0 else 0)) * k
            xb = (MARGEM_X + self.sw * (i + 1) + (20 if i == self.n - 1 else 0)) * k
            pts += [(xa, yb - h * k), (xb, yb - h * k)]
        pts.append((pts[-1][0], yb))
        # soft side shading, then the outlined block
        d.polygon([(x + 10 * k, y + 10 * k) for x, y in pts], fill=DEGRAU_LADO)
        d.polygon(pts, fill=DEGRAU, outline=TRACO, width=lw)
        for i, h in enumerate(hs):  # thin tread lines
            xa = (MARGEM_X + self.sw * i) * k
            y = yb - h * k + 14 * k
            d.line([(xa + (0 if i else -20 * k) + 8 * k, y), (xa + self.sw * k - 8 * k, y)], fill=DEGRAU_LADO,
                   width=max(1, round(3 * k)))
        return img.resize((self.largura, self.altura), Image.Resampling.LANCZOS)

    def desenhar(self, item_atual: int | None = None, estados: list[EstadoFigura] | None = None,
                 tags: bool = True, rotulos: list[str] | None = None) -> Image.Image:
        """Stage image (RGB, largura x altura) with every figure and tag (`rotulos` overrides tag texts)."""
        estados = estados or [EstadoFigura() for _ in range(self.n)]
        img = self.fundo.copy()
        sombra = ImageDraw.Draw(img, "RGBA")
        for i, (it, pos, est) in enumerate(zip(self.r.itens, self.posicoes, estados)):
            alt = round(self._k(pos.altura))
            fig = fr.renderizar(it.personagem, alt, est.expressao, est.boca, est.piscando)
            if est.esticar != 1.0:
                fig = fig.resize((round(fig.width / est.esticar ** 0.5), round(fig.height * est.esticar)),
                                 Image.Resampling.BILINEAR)
            if est.opacidade < 0.999:
                fig = fig.copy()
                fig.putalpha(fig.getchannel("A").point(lambda v, k=est.opacidade: int(v * k)))
            x = self._k(pos.x)
            pe = self._y(pos.chao)
            rx = self._k(self.sw * 0.3)
            sombra.ellipse([x - rx, pe - self._k(9), x + rx, pe + self._k(7)], fill=(30, 30, 40, 40))
            topo_canvas = pe - fig.height * (fr.CHAO_U / fr.ALT_U) + self._k(est.dy)
            img.paste(fig, (round(x - fig.width / 2), round(topo_canvas)), fig)
        if tags:
            for i, (it, pos) in enumerate(zip(self.r.itens, self.posicoes)):
                t = tag(rotulos[i] if rotulos else it.rotulo, i == item_atual, int(self.sw - 10), self.escala)
                ty = self._y(pos.topo_cabeca) - self._k(14) - t.height + self._k(estados[i].dy)
                img.paste(t, (round(self._k(pos.x) - t.width / 2), round(ty)), t)
        return img


# --- full frames ---------------------------------------------------------------------
def quadro(ranking: Ranking, item_atual: int | None = None, estados: list[EstadoFigura] | None = None,
           palco: Palco | None = None) -> Image.Image:
    """Static full frame (no camera move): title, stage, yellow label of the current item."""
    palco = palco or Palco(ranking)
    img = Image.new("RGB", (L, A), FUNDO)
    img.paste(palco.desenhar(item_atual, estados), (0, PALCO_Y0))
    desenhar_titulo(img, ranking.titulo)
    if item_atual is not None:
        desenhar_rotulo(img, ranking.itens[item_atual].rotulo)
    return img
