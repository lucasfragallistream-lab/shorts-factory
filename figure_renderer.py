"""Parametric flat characters in the style of docs/referencia_estilo.png.

A figure is drawn in layers (back hair, backpack, legs, shoes, body/clothes, arms, held items,
neck, ears, head, hair, face, head accessories) on a 340x600 unit canvas whose floor is y=596.
Units are scaled to the requested height and supersampled (config.SUPERSAMPLING) before a LANCZOS
reduction, so outlines stay clean. No texture, flat colors, dark outline.

Public API:
    renderizar(personagem, altura, expressao=None, boca="fechada", piscando=False) -> RGBA image
    topo(personagem) -> fraction (0..1) of the canvas height where the figure's head/hair starts
"""
from __future__ import annotations

import json
from functools import lru_cache

from PIL import Image, ImageDraw

import config
from schemas import Personagem

SS = config.SUPERSAMPLING
LARG_U, ALT_U = 340, 600  # canvas in units
CHAO_U = 596  # floor line (bottom of the shoes)
CX = LARG_U / 2
TRACO = (38, 40, 50, 255)
LW = 4.2  # outline width in units

BOCAS = ("fechada", "aberta")

PELE = {"clara": (250, 218, 190), "media": (238, 188, 146), "morena": (198, 140, 98), "negra": (128, 86, 60)}
CORES = {
    "azul": (62, 138, 214), "azul_claro": (146, 200, 238), "vermelho": (222, 76, 72), "verde": (88, 172, 106),
    "amarelo": (248, 202, 72), "roxo": (142, 100, 192), "laranja": (244, 142, 62), "rosa": (242, 146, 176),
    "cinza": (152, 158, 168), "preto": (64, 66, 76), "branco": (246, 246, 246), "bege": (226, 202, 162),
}
CABELO = {"preto": (46, 42, 48), "castanho": (112, 72, 44), "loiro": (240, 200, 100), "ruivo": (204, 96, 48),
          "grisalho": (172, 172, 176), "branco": (236, 236, 236)}
CALCA = {"camiseta": (60, 88, 136), "moletom": (128, 132, 142), "camisa": (222, 200, 160), "social": (86, 90, 102),
         "jaqueta": (60, 88, 136), "vestido": (60, 88, 136)}
SAPATO = (52, 54, 64)
BRANCO = (255, 255, 255)

# idade -> (height factor, head/height, torso/height, torso width / head width)
_PROP = {
    "crianca": (0.64, 0.37, 0.25, 0.84),
    "adolescente": (0.79, 0.31, 0.28, 0.88),
    "jovem": (0.90, 0.28, 0.29, 0.94),
    "adulto": (0.94, 0.27, 0.30, 1.00),
    "meia_idade": (0.94, 0.27, 0.30, 1.12),
    "idoso": (0.88, 0.28, 0.30, 1.02),
}


def _mudar(c, f: float):
    """Darken (f < 1) or lighten (f > 1) a color."""
    if f <= 1:
        return tuple(int(v * f) for v in c[:3])
    return tuple(int(v + (255 - v) * (f - 1)) for v in c[:3])


def _rgba(c):
    if c is None:
        return None
    c = tuple(int(v) for v in c)
    return c if len(c) == 4 else c + (255,)


class _Pincel:
    def __init__(self, img: Image.Image, k: float, ox: float = 0.0):
        self.d = ImageDraw.Draw(img)
        self.k = k
        self.ox = ox  # x offset in units (wider canvas for poses)

    def _b(self, b):
        x0, y0, x1, y1 = b
        x0, x1 = x0 + self.ox, x1 + self.ox
        return [min(x0, x1) * self.k, min(y0, y1) * self.k, max(x0, x1) * self.k, max(y0, y1) * self.k]

    def _w(self, w):
        return max(1, round((LW if w is None else w) * self.k))

    def elipse(self, b, cor, contorno=TRACO, w=None):
        self.d.ellipse(self._b(b), fill=_rgba(cor), outline=_rgba(contorno), width=self._w(w))

    def ret(self, b, cor, raio=0.0, contorno=TRACO, w=None):
        bb = self._b(b)
        r = min(raio * self.k, (bb[2] - bb[0]) / 2, (bb[3] - bb[1]) / 2)
        self.d.rounded_rectangle(bb, radius=max(r, 0), fill=_rgba(cor), outline=_rgba(contorno), width=self._w(w))

    def poli(self, pts, cor, contorno=TRACO, w=None):
        self.d.polygon([((x + self.ox) * self.k, y * self.k) for x, y in pts], fill=_rgba(cor), outline=_rgba(contorno),
                       width=self._w(w))

    def linha(self, pts, cor=TRACO, w=None):
        lw = self._w(w)
        p = [((x + self.ox) * self.k, y * self.k) for x, y in pts]
        self.d.line(p, fill=_rgba(cor), width=lw, joint="curve")
        r = lw / 2
        for x, y in (p[0], p[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=_rgba(cor))

    def arco(self, b, ini, fim, cor=TRACO, w=None):
        self.d.arc(self._b(b), ini, fim, fill=_rgba(cor), width=self._w(w))

    def corda(self, b, ini, fim, cor, contorno=TRACO, w=None):
        self.d.chord(self._b(b), ini, fim, fill=_rgba(cor), outline=_rgba(contorno), width=self._w(w))


class _Geo:
    """Body measurements in units for one character."""

    def __init__(self, p: Personagem):
        fa, fc, ft, fl = _PROP[p.idade]
        if p.sexo == "feminino":
            fa *= 0.97
        self.H = H = 592 * fa
        self.topo = CHAO_U - H
        self.d = d = H * fc  # head height
        self.wh = d * 0.92  # head width
        self.x0, self.x1 = CX - self.wh / 2, CX + self.wh / 2
        self.y0, self.y1 = self.topo, self.topo + d
        self.ys = self.y1 + H * 0.012  # shoulders
        self.ht = H * ft
        self.yq = self.ys + self.ht  # hips
        self.wt = self.wh * fl * (0.94 if p.sexo == "feminino" else 1.0)
        self.hs = H * 0.045  # shoe height
        self.ype = CHAO_U - self.hs  # ankle line
        self.wa = max(20.0, self.wt * 0.2)  # arm width
        self.ybraco = self.yq + H * 0.07  # wrist
        self.rmao = self.wa * 0.62
        self.olho_y = self.y0 + d * 0.55
        self.olho_dx = self.wh * 0.18
        self.boca_y = self.y0 + d * 0.76
        self.perna_w = self.wt * 0.36

    def braco_x(self, lado: int) -> tuple[float, float]:
        """Arm x-range; lado -1 = viewer left, +1 = viewer right."""
        if lado < 0:
            return CX - self.wt / 2 - self.wa + 5, CX - self.wt / 2 + 5
        return CX + self.wt / 2 - 5, CX + self.wt / 2 + self.wa - 5

    def mao(self, lado: int) -> tuple[float, float]:
        a, b = self.braco_x(lado)
        return (a + b) / 2, self.ybraco


# --- layers ------------------------------------------------------------------
def _cabelo_tras(pn: _Pincel, g: _Geo, p: Personagem):
    cor = CABELO[p.cor_cabelo]
    if p.cabelo == "comprido":
        pn.ret((g.x0 - 7, g.y0 + g.d * 0.25, g.x1 + 7, g.y0 + g.d * 1.32), cor, raio=g.wh * 0.3)
    elif p.cabelo == "coque":
        r = g.d * 0.17
        pn.elipse((CX - r, g.y0 - r * 1.35, CX + r, g.y0 + r * 0.65), cor)
    elif p.cabelo == "rabo":
        pn.elipse((g.x1 - g.wh * 0.12, g.y0 + g.d * 0.2, g.x1 + g.wh * 0.22, g.y0 + g.d * 0.95), cor)


def _mochila_tras(pn: _Pincel, g: _Geo, p: Personagem):
    if "mochila" in p.acessorios:
        cor = CORES["vermelho"] if p.cor_roupa in ("azul", "azul_claro", "verde", "preto", "cinza") else CORES["azul"]
        pn.ret((CX - g.wt * 0.64, g.ys + g.ht * 0.06, CX + g.wt * 0.64, g.yq + g.ht * 0.04), _mudar(cor, 0.85),
               raio=g.wa * 0.7)


def _pernas(pn: _Pincel, g: _Geo, p: Personagem):
    pele = PELE[p.pele]
    calca = CALCA[p.roupa]
    curto = p.roupa == "vestido" or (p.idade == "crianca" and p.roupa == "camiseta")
    if p.idade == "crianca" and p.roupa == "camiseta":
        calca = _mudar(CORES[p.cor_roupa], 0.72)
    gap = g.wt * 0.035
    pernas = [(CX - gap - g.perna_w, CX - gap), (CX + gap, CX + gap + g.perna_w)]
    for a, b in pernas:
        pn.ret((a, g.yq - 10, b, g.ype + 2), pele if curto else calca, raio=4)
    # shoes
    for i, (a, b) in enumerate(pernas):
        sapato = CORES["azul"] if p.idade == "crianca" else SAPATO
        ext = g.perna_w * 0.22
        pn.ret((a - (ext if i == 0 else 2), g.ype - 2, b + (2 if i == 0 else ext), CHAO_U), sapato,
               raio=g.hs * 0.6)
        if p.idade == "crianca":
            pn.linha([(a - ext * 0.6 if i == 0 else a + 2, CHAO_U - g.hs * 0.35),
                      (b - 2 if i == 0 else b + ext * 0.6, CHAO_U - g.hs * 0.35)], BRANCO, w=3)
    if p.roupa == "vestido":
        return
    # hips / shorts
    comp = (g.ype - g.yq)
    fundo = g.yq + comp * (0.38 if curto else 0.16)
    pn.ret((CX - g.wt / 2 + 3, g.yq - 14, CX + g.wt / 2 - 3, fundo), calca, raio=4)
    if curto:
        for a, b in pernas:
            pn.ret((a - 2, g.yq, b + 2, fundo), calca, raio=4)
    pn.linha([(CX, g.yq + 2), (CX, fundo - 2)], _mudar(calca, 0.6), w=2.5)


def _torso(pn: _Pincel, g: _Geo, p: Personagem):
    cor = CORES[p.cor_roupa]
    x0, x1 = CX - g.wt / 2, CX + g.wt / 2
    caixa = (x0, g.ys, x1, g.yq + 4)
    r = g.wa * 0.85
    if p.roupa == "jaqueta":
        pn.ret(caixa, BRANCO, raio=r)
        pn.ret((x0, g.ys, CX - g.wt * 0.13, g.yq + 4), cor, raio=r * 0.6)
        pn.ret((CX + g.wt * 0.13, g.ys, x1, g.yq + 4), cor, raio=r * 0.6)
        return
    pn.ret(caixa, cor, raio=r)
    if p.roupa == "vestido":
        comp = g.ype - g.yq
        pn.poli([(x0 + 4, g.yq - g.ht * 0.12), (x1 - 4, g.yq - g.ht * 0.12),
                 (x1 + g.wt * 0.2, g.yq + comp * 0.5), (x0 - g.wt * 0.2, g.yq + comp * 0.5)], cor)
    elif p.roupa == "moletom":
        bolso = (CX - g.wt * 0.3, g.yq - g.ht * 0.36, CX + g.wt * 0.3, g.yq - g.ht * 0.06)
        pn.ret(bolso, _mudar(cor, 0.92), raio=6, w=3)
        pn.elipse((CX - g.wt * 0.36, g.ys - 12, CX + g.wt * 0.36, g.ys + g.ht * 0.16), _mudar(cor, 0.82))
        for dx in (-0.09, 0.09):
            pn.linha([(CX + g.wt * dx, g.ys + g.ht * 0.12), (CX + g.wt * dx, g.ys + g.ht * 0.32)], BRANCO, w=3)
    elif p.roupa in ("camisa", "social"):
        for i in range(4):
            y = g.ys + g.ht * (0.22 + 0.19 * i)
            pn.elipse((CX - 2.6, y - 2.6, CX + 2.6, y + 2.6), _mudar(cor, 0.55), contorno=None)
        if p.roupa == "social":
            pn.ret((x0 + g.wt * 0.62, g.ys + g.ht * 0.2, x0 + g.wt * 0.84, g.ys + g.ht * 0.34), cor, raio=2, w=2.5)


def _braco(pn: _Pincel, g: _Geo, p: Personagem, lado: int):
    pele = PELE[p.pele]
    cor = CORES[p.cor_roupa]
    a, b = g.braco_x(lado)
    longo = p.roupa in ("moletom", "camisa", "social", "jaqueta")
    pn.ret((a, g.ys + 4, b, g.ybraco), _mudar(cor, 0.94) if longo else pele, raio=g.wa / 2)
    if not longo:
        pn.ret((a - 2, g.ys + 2, b + 2, g.ys + g.ht * 0.36), cor, raio=g.wa / 2)
    elif p.roupa in ("camisa", "social", "moletom"):
        pn.linha([(a + 2, g.ybraco - g.wa * 0.5), (b - 2, g.ybraco - g.wa * 0.5)], _mudar(cor, 0.6), w=2.5)


def _mao(pn: _Pincel, g: _Geo, p: Personagem, lado: int):
    x, y = g.mao(lado)
    r = g.rmao
    pn.elipse((x - r, y - r, x + r, y + r), PELE[p.pele])


def _itens_mao(p: Personagem) -> dict[int, str]:
    """Held items -> hand side (+1 viewer right first, then -1)."""
    out: dict[int, str] = {}
    for item in ("caneca", "bengala", "celular", "sacola"):
        if item in p.acessorios:
            for lado in (1, -1):
                if lado not in out:
                    out[lado] = item
                    break
    return out


def _item_atras(pn: _Pincel, g: _Geo, item: str, lado: int):
    x, y = g.mao(lado)
    w = g.wa
    if item == "bengala":
        bx = x + lado * w * 0.55
        pn.linha([(bx, y - w * 0.4), (bx, CHAO_U - 2)], (120, 78, 46), w=7)
        pn.arco((bx - w * 0.9 if lado > 0 else bx, y - w * 1.1, bx if lado > 0 else bx + w * 0.9, y + w * 0.2),
                180, 360, (120, 78, 46), w=7)
    elif item == "sacola":
        pn.arco((x - w * 0.7, y - w * 0.4, x + w * 0.7, y + w * 1.4), 180, 360, TRACO, w=3)
        pn.poli([(x - w * 1.0, y + w * 0.6), (x + w * 1.0, y + w * 0.6), (x + w * 1.2, y + w * 2.6),
                 (x - w * 1.2, y + w * 2.6)], (214, 176, 120))


def _item_frente(pn: _Pincel, g: _Geo, item: str, lado: int):
    x, y = g.mao(lado)
    w = g.wa
    if item == "caneca":
        cx0 = x + w * 0.35 * lado
        a, b = cx0 - w * 0.75, cx0 + w * 0.75
        alca_x = b if lado > 0 else a
        pn.elipse((alca_x - w * 0.45, y - w * 1.0, alca_x + w * 0.45, y - w * 0.1), None, w=4)
        pn.ret((a, y - w * 1.5, b, y + w * 0.35), BRANCO, raio=4)
        pn.linha([(a + 3, y - w * 0.85), (b - 3, y - w * 0.85)], CORES["vermelho"], w=5)
    elif item == "celular":
        pn.ret((x - w * 0.5, y - w * 1.6, x + w * 0.5, y + w * 0.1), (40, 44, 56), raio=5, w=3)
        pn.ret((x - w * 0.35, y - w * 1.43, x + w * 0.35, y - w * 0.08), (120, 190, 240), raio=2, contorno=None)


def _torso_frente(pn: _Pincel, g: _Geo, p: Personagem):
    """Things worn over the torso: backpack straps, tie, necklace, shirt collar."""
    cor = CORES[p.cor_roupa]
    if p.roupa in ("camisa", "social"):
        cl = _mudar(cor, 1.25)
        pn.poli([(CX - g.wh * 0.17, g.ys - 3), (CX, g.ys + g.ht * 0.1), (CX - g.wh * 0.02, g.ys - 3)], cl, w=3)
        pn.poli([(CX + g.wh * 0.17, g.ys - 3), (CX, g.ys + g.ht * 0.1), (CX + g.wh * 0.02, g.ys - 3)], cl, w=3)
    if "gravata" in p.acessorios:
        tc = (40, 60, 120) if p.cor_roupa in ("vermelho", "rosa", "laranja") else (196, 56, 60)
        y = g.ys + g.ht * 0.06
        pn.poli([(CX - 7, y), (CX + 7, y), (CX + 4, y + 11), (CX - 4, y + 11)], tc, w=3)
        pn.poli([(CX - 4, y + 10), (CX + 4, y + 10), (CX + 10, g.yq - g.ht * 0.18), (CX, g.yq - g.ht * 0.06),
                 (CX - 10, g.yq - g.ht * 0.18)], tc, w=3)
    if "mochila" in p.acessorios:
        cor_m = CORES["vermelho"] if p.cor_roupa in ("azul", "azul_claro", "verde", "preto", "cinza") else CORES["azul"]
        for dx in (-0.3, 0.3):
            xa = CX + g.wt * dx
            pn.ret((xa - g.wt * 0.055, g.ys - 2, xa + g.wt * 0.055, g.ys + g.ht * 0.72), _mudar(cor_m, 0.85),
                   raio=3, w=3)
    if "colar" in p.acessorios:
        import math
        for i in range(9):
            t = math.pi * i / 8
            bx = CX - g.wt * 0.2 * math.cos(t)
            by = g.ys + 2 + g.ht * 0.2 * math.sin(t)
            pn.elipse((bx - 3.5, by - 3.5, bx + 3.5, by + 3.5), (250, 214, 90), w=1.5)


def _pescoco(pn: _Pincel, g: _Geo, p: Personagem):
    pele = PELE[p.pele]
    pn.ret((CX - g.wh * 0.13, g.y1 - g.d * 0.1, CX + g.wh * 0.13, g.ys + 8), _mudar(pele, 0.9), raio=4, w=3)


def _orelhas(pn: _Pincel, g: _Geo, p: Personagem):
    r = g.d * 0.085
    y = g.olho_y + g.d * 0.04
    for x in (g.x0 + 3, g.x1 - 3):
        pn.elipse((x - r, y - r, x + r, y + r), PELE[p.pele])


def _cabeca(pn: _Pincel, g: _Geo, p: Personagem):
    pn.elipse((g.x0, g.y0, g.x1, g.y1), PELE[p.pele])


def _capa(pn: _Pincel, g: _Geo, cor, varrido: bool = False):
    """Short hair: cap over the skull, sideburns and a jagged fringe (swept to one side if `varrido`)."""
    import math
    x0, x1, y0, d, wh = g.x0, g.x1, g.y0, g.d, g.wh
    a, cy = wh / 2 + 4, y0 + d * 0.4
    b = cy - (y0 - 6)
    pts = [(CX + a * math.cos(math.radians(t)), cy + b * math.sin(math.radians(t))) for t in range(180, 361, 10)]
    pts += [(x1 - 1, y0 + d * 0.56), (x1 - wh * 0.1, y0 + d * 0.5)]
    n = 6
    for i in range(n + 1):
        f = i / n
        x = x1 - wh * 0.1 - (wh * 0.8) * f
        if varrido:
            y = cy + d * (0.02 + 0.12 * f) if i % 2 == 0 else cy - d * (0.02 - 0.05 * f)
        else:
            y = cy + d * 0.06 if i % 2 == 0 else cy - d * 0.01
        pts.append((x, y))
    pts += [(x0 + 1, y0 + d * 0.56), (x0 - 4, cy)]
    pn.poli(pts, cor)


def _cabelo_frente(pn: _Pincel, g: _Geo, p: Personagem):
    cor = CABELO[p.cor_cabelo]
    x0, x1, y0, d, wh = g.x0, g.x1, g.y0, g.d, g.wh
    if p.cabelo == "careca":
        if p.idade in ("meia_idade", "idoso"):
            for x in (x0 + wh * 0.06, x1 - wh * 0.06):
                pn.elipse((x - wh * 0.09, y0 + d * 0.3, x + wh * 0.09, y0 + d * 0.55), cor, w=3)
        return
    capa = (x0 - 4, y0 - 6, x1 + 4, y0 + d * 0.8)
    if p.cabelo == "cacheado":
        import math
        pn.corda(capa, 180, 360, cor)
        r = d * 0.12
        a, b = (x1 - x0) / 2 + 2, d * 0.43
        cy = y0 - 6 + (d * 0.8 + 6) / 2
        for i in range(9):
            t = math.radians(180 + 180 * i / 8)
            px, py = CX + a * math.cos(t), cy + b * math.sin(t)
            pn.elipse((px - r, py - r, px + r, py + r), cor)
        return
    if p.cabelo == "espetado":
        pts = []
        n = 7
        for i in range(n + 1):
            x = x0 - 2 + (wh + 4) * i / n
            pts.append((x, y0 + d * 0.12 if i in (0, n) else (y0 - d * 0.08 if i % 2 else y0 + d * 0.06)))
        pn.poli([(x0 - 2, y0 + d * 0.3)] + pts + [(x1 + 2, y0 + d * 0.3)], cor)
        pn.corda(capa, 180, 360, cor)
        return
    if p.cabelo in ("curto", "liso"):
        _capa(pn, g, cor, varrido=p.cabelo == "liso")
        return
    pn.corda(capa, 180, 360, cor)
    if p.cabelo == "comprido":
        for lado in (-1, 1):
            xa = x0 - 5 if lado < 0 else x1 - wh * 0.16
            pn.ret((xa, y0 + d * 0.25, xa + wh * 0.21, y0 + d * 0.95), cor, raio=wh * 0.1)
        pn.corda(capa, 180, 360, cor)


def _rosto(pn: _Pincel, g: _Geo, p: Personagem, expressao: str, boca: str, piscando: bool):
    pele = PELE[p.pele]
    d, wh = g.d, g.wh
    ey, dx = g.olho_y, g.olho_dx
    pelo = CABELO[p.cor_cabelo] if p.cabelo != "careca" else CABELO["grisalho" if p.idade == "idoso" else "preto"]
    if "barba" in p.acessorios:
        pn.corda((g.x0 + 1, g.y0 + d * 0.22, g.x1 - 1, g.y0 + d * 1.08), 0, 180, pelo)
        pn.elipse((CX - wh * 0.17, g.boca_y - d * 0.07, CX + wh * 0.17, g.boca_y + d * 0.08), pele, contorno=None)
    if p.idade in ("crianca", "adolescente") and expressao != "cansado":
        bochecha = tuple(int(0.65 * a + 0.35 * b) for a, b in zip(pele, (240, 120, 120)))
        for x in (CX - dx * 1.45, CX + dx * 1.45):
            pn.elipse((x - d * 0.06, ey + d * 0.08, x + d * 0.06, ey + d * 0.13), bochecha, contorno=None)
    # eyes
    r = d * 0.052
    for x in (CX - dx, CX + dx):
        if piscando:
            pn.arco((x - r * 1.2, ey - r, x + r * 1.2, ey + r), 10, 170, w=3.5)
        elif expressao == "chocado":
            rr = r * 1.6
            pn.elipse((x - rr, ey - rr, x + rr, ey + rr), BRANCO, w=3)
            pn.elipse((x - r * 0.8, ey - r * 0.8, x + r * 0.8, ey + r * 0.8), TRACO, contorno=None)
        elif expressao == "cansado":
            pn.corda((x - r, ey - r, x + r, ey + r), 0, 180, TRACO, contorno=None)
            pn.linha([(x - r * 1.3, ey), (x + r * 1.3, ey)], w=3)
            pn.arco((x - r * 1.1, ey + r * 0.6, x + r * 1.1, ey + r * 2.0), 20, 160, _mudar(pele, 0.7), w=2.5)
        else:
            pn.elipse((x - r, ey - r * 1.1, x + r, ey + r * 1.1), TRACO, contorno=None)
            h = r * 0.38
            pn.elipse((x + r * 0.15, ey - r * 0.6, x + r * 0.15 + 2 * h, ey - r * 0.6 + 2 * h), BRANCO, contorno=None)
            if expressao == "raiva":  # heavy upper lid, slanted to the nose
                s_ = -1 if x < CX else 1
                pn.poli([(x - r * 1.5, ey - r * (1.5 if s_ < 0 else 0.4)), (x + r * 1.5, ey - r * (0.4 if s_ < 0 else 1.5)),
                         (x + r * 1.5, ey - r * 2.2), (x - r * 1.5, ey - r * 2.2)], pele, contorno=None)
    if expressao == "triste" and not piscando:  # tears
        for x in (CX - dx, CX + dx):
            pn.poli([(x - r * 0.45, ey + r * 1.9), (x, ey + r * 1.1), (x + r * 0.45, ey + r * 1.9),
                     (x, ey + r * 2.6)], (110, 190, 245), w=2)
            pn.linha([(x, ey + r * 2.6), (x - r * 0.2, ey + r * 4.2)], (110, 190, 245), w=3)
    # brows
    by = ey - d * 0.13
    bl = wh * 0.08
    for s in (-1, 1):
        x = CX + s * dx
        if expressao in ("preocupado", "triste"):
            pn.linha([(x - s * bl, by - 7), (x + s * bl, by + 1)], pelo, w=4)
        elif expressao == "raiva":
            pn.linha([(x - s * bl, by + 5), (x + s * bl, by - 9)], pelo, w=5.5)
        elif expressao == "chocado":
            pn.arco((x - bl, by - 12, x + bl, by + 2), 200, 340, pelo, w=4)
        elif expressao == "cansado":
            pn.linha([(x - bl, by + 3), (x + bl, by + 3)], pelo, w=4)
        else:
            pn.arco((x - bl, by - 5, x + bl, by + 5), 200, 340, pelo, w=4)
    if "bigode" in p.acessorios:
        pn.poli([(CX - wh * 0.15, g.boca_y - d * 0.02), (CX, g.boca_y - d * 0.09), (CX + wh * 0.15, g.boca_y - d * 0.02),
                 (CX, g.boca_y - d * 0.04)], pelo, w=3)
    # mouth
    my, mw = g.boca_y, wh * 0.24
    interior = (120, 40, 52)
    if expressao == "chocado":
        k = 1.0 if boca == "fechada" else 1.35
        pn.elipse((CX - mw * 0.2 * k, my - mw * 0.2 * k, CX + mw * 0.2 * k, my + mw * 0.32 * k), interior, w=3)
    elif boca == "aberta":
        if expressao == "feliz":
            pn.corda((CX - mw / 2, my - mw * 0.4, CX + mw / 2, my + mw * 0.4), 0, 180, interior, w=3)
            pn.corda((CX - mw * 0.25, my + mw * 0.12, CX + mw * 0.25, my + mw * 0.42), 180, 360, (232, 120, 130),
                     contorno=None)
        elif expressao == "raiva":  # shouting: wide mouth with teeth
            pn.ret((CX - mw * 0.42, my - mw * 0.1, CX + mw * 0.42, my + mw * 0.34), interior, raio=mw * 0.12, w=3)
            pn.ret((CX - mw * 0.36, my - mw * 0.06, CX + mw * 0.36, my + mw * 0.06), BRANCO, raio=2, contorno=None)
        else:
            pn.elipse((CX - mw * 0.28, my - mw * 0.12, CX + mw * 0.28, my + mw * 0.26), interior, w=3)
    else:
        if expressao == "feliz":
            pn.arco((CX - mw / 2, my - mw * 0.4, CX + mw / 2, my + mw * 0.4), 20, 160, w=3.5)
        elif expressao in ("preocupado", "triste"):
            pn.arco((CX - mw * 0.4, my + mw * 0.05, CX + mw * 0.4, my + mw * 0.5), 205, 335, w=3.5)
        elif expressao == "raiva":
            pn.arco((CX - mw * 0.45, my + mw * 0.0, CX + mw * 0.45, my + mw * 0.45), 210, 330, w=4.5)
        else:
            pn.linha([(CX - mw * 0.3, my + mw * 0.08), (CX + mw * 0.3, my + mw * 0.08)], w=3.5)


def _acessorios_cabeca(pn: _Pincel, g: _Geo, p: Personagem):
    d, wh = g.d, g.wh
    if "oculos" in p.acessorios:
        r = d * 0.105
        for x in (CX - g.olho_dx, CX + g.olho_dx):
            pn.elipse((x - r, g.olho_y - r, x + r, g.olho_y + r), (255, 255, 255, 60), w=3.5)
        pn.linha([(CX - g.olho_dx + r, g.olho_y - 2), (CX + g.olho_dx - r, g.olho_y - 2)], w=3)
        pn.linha([(CX - g.olho_dx - r, g.olho_y - 3), (g.x0 + 2, g.olho_y - 6)], w=3)
        pn.linha([(CX + g.olho_dx + r, g.olho_y - 3), (g.x1 - 2, g.olho_y - 6)], w=3)
    if "bone" in p.acessorios:
        cor = CORES["vermelho"] if p.cor_roupa != "vermelho" else CORES["azul"]
        pn.corda((g.x0 - 4, g.y0 - 10, g.x1 + 4, g.y0 + d * 0.62), 180, 360, cor)
        pn.ret((g.x0 - wh * 0.28, g.y0 + d * 0.22, CX + wh * 0.1, g.y0 + d * 0.31), _mudar(cor, 0.85), raio=5)
        pn.elipse((CX - 5, g.y0 - 14, CX + 5, g.y0 - 4), cor, w=2.5)
    if "fone" in p.acessorios:
        pn.arco((g.x0 - 6, g.y0 - 12, g.x1 + 6, g.y0 + d * 0.9), 185, 355, (50, 52, 62), w=8)
        y = g.olho_y + d * 0.03
        for x in (g.x0 - 2, g.x1 + 2):
            pn.ret((x - d * 0.07, y - d * 0.12, x + d * 0.07, y + d * 0.12), (60, 62, 74), raio=6)


# --- poses (articulated arms) ------------------------------------------------
POSES = ("parado", "aponta", "estende", "bracos_cima", "maos_rosto", "maos_cintura", "mao_peito", "abraca")
MARGEM_POSE = 120  # extra units on each side of the canvas so stretched arms fit


def _ombro(g: _Geo, lado: int) -> tuple[float, float]:
    return CX + lado * (g.wt / 2 - g.wa * 0.35), g.ys + g.wa * 0.5


def _ik(s, w, l1: float, l2: float, lado: int):
    """Two-bone arm: elbow position for shoulder s and wrist target w, elbow bent outward (lado side)."""
    import math

    dx, dy = w[0] - s[0], w[1] - s[1]
    d = max(1e-3, min(math.hypot(dx, dy), l1 + l2 - 1e-3))
    base = math.atan2(dy, dx)
    th = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    opc = [(s[0] + l1 * math.cos(base + sg * th), s[1] + l1 * math.sin(base + sg * th)) for sg in (1, -1)]
    cot = max(opc, key=lambda e: e[0] * lado + e[1] * 0.15)  # outward, slightly down
    # if the target is out of reach, put the wrist at full stretch along the line
    w2 = (s[0] + (l1 + l2) * math.cos(base), s[1] + (l1 + l2) * math.sin(base)) if math.hypot(dx, dy) > l1 + l2 else w
    return cot, w2


def _alvos(g: _Geo, pose: str) -> dict[int, tuple]:
    """Wrist targets per arm: lado -> (wrist, pointing finger?, open hand?). Missing arm = resting."""
    braco = g.ybraco - g.ys
    out: dict[int, tuple] = {}
    if pose == "aponta":
        sx, sy = _ombro(g, 1)
        out[1] = ((sx + braco * 1.05, sy - braco * 0.12), True, False)
    elif pose == "estende":
        sx, sy = _ombro(g, 1)
        out[1] = ((sx + braco * 1.0, sy + braco * 0.12), False, True)
    elif pose == "bracos_cima":
        for lado in (-1, 1):
            sx, sy = _ombro(g, lado)
            out[lado] = ((sx + lado * braco * 0.5, sy - braco * 0.82), False, True)
    elif pose == "maos_rosto":
        for lado in (-1, 1):
            out[lado] = ((CX + lado * g.wh * 0.17, g.olho_y + g.d * 0.12), False, True,
                         (CX + lado * g.wt * 0.42, g.ys + g.ht * 0.62))  # fixed elbow: face in hands
    elif pose == "maos_cintura":
        for lado in (-1, 1):
            out[lado] = ((CX + lado * (g.wt / 2 + 1), g.yq - g.ht * 0.12), False, False)
    elif pose == "mao_peito":
        out[1] = ((CX + g.wt * 0.06, g.ys + g.ht * 0.34), False, True)
    elif pose == "abraca":
        for lado in (-1, 1):
            sx, sy = _ombro(g, lado)
            out[lado] = ((sx + lado * braco * 0.85, sy + braco * 0.3), False, True)
    return out


def _braco_pose(pn: _Pincel, g: _Geo, p: Personagem, lado: int, alvo: tuple):
    import math

    pulso, dedo, aberta = alvo[:3]
    pele = PELE[p.pele]
    cor = CORES[p.cor_roupa]
    longo = p.roupa in ("moletom", "camisa", "social", "jaqueta")
    s = _ombro(g, lado)
    meio = (g.ybraco - g.ys) / 2 * 1.02
    if len(alvo) > 3:
        e, w = alvo[3], pulso
    else:
        e, w = _ik(s, pulso, meio, meio, lado)
    wa = g.wa
    pn.linha([s, e, w], TRACO, w=wa + 2 * LW)
    pn.linha([s, e, w], _mudar(cor, 0.94) if longo else pele, w=wa)
    if not longo:  # short sleeve over the upper arm
        m = (s[0] + (e[0] - s[0]) * 0.72, s[1] + (e[1] - s[1]) * 0.72)
        pn.linha([s, m], TRACO, w=wa + 4 + 2 * LW)
        pn.linha([s, m], cor, w=wa + 4)
    ux, uy = w[0] - e[0], w[1] - e[1]
    n = math.hypot(ux, uy) or 1.0
    ux, uy = ux / n, uy / n
    r = g.rmao
    if dedo:  # index finger along the forearm direction
        f = (w[0] + ux * r * 2.0, w[1] + uy * r * 2.0)
        pn.linha([w, f], TRACO, w=r * 0.62 + 2 * LW)
        pn.linha([w, f], pele, w=r * 0.62)
    hx, hy = w[0] + ux * r * 0.3, w[1] + uy * r * 0.3
    rr = r * (1.12 if aberta else 1.0)
    pn.elipse((hx - rr, hy - rr * (1.08 if aberta else 1), hx + rr, hy + rr * (1.08 if aberta else 1)), pele)
    if aberta:  # finger lines
        for k in (-0.35, 0.0, 0.35):
            px, py = -uy, ux
            a = (hx + ux * rr * 0.2 + px * rr * k, hy + uy * rr * 0.2 + py * rr * k)
            b = (hx + ux * rr * 0.85 + px * rr * k, hy + uy * rr * 0.85 + py * rr * k)
            pn.linha([a, b], _mudar(pele, 0.72), w=2)


# --- public API --------------------------------------------------------------
def topo(p: Personagem) -> float:
    """Fraction of the canvas height where the figure (hair/hat included) starts."""
    g = _Geo(p)
    extra = g.d * 0.22 if p.cabelo == "coque" else (g.d * 0.1 if p.cabelo in ("espetado", "cacheado") else 0.04 * g.d)
    return max(0.0, (g.y0 - extra) / ALT_U)


def proporcao() -> float:
    """Canvas width / height."""
    return LARG_U / ALT_U


def _desenhar(p: Personagem, altura: int, expressao: str, boca: str, piscando: bool, pose: str = "parado",
              margem: float = 0.0) -> Image.Image:
    k = altura / ALT_U * SS
    img = Image.new("RGBA", (round((LARG_U + 2 * margem) * k), round(ALT_U * k)), (0, 0, 0, 0))
    pn = _Pincel(img, k, margem)
    g = _Geo(p)
    alvos = _alvos(g, pose)
    maos = {lado: item for lado, item in _itens_mao(p).items() if lado not in alvos}
    _cabelo_tras(pn, g, p)
    _mochila_tras(pn, g, p)
    for lado, item in maos.items():
        if item in ("bengala", "sacola"):
            _item_atras(pn, g, item, lado)
    _pernas(pn, g, p)
    _torso(pn, g, p)
    for lado in (-1, 1):
        if lado not in alvos:
            _braco(pn, g, p, lado)
            _mao(pn, g, p, lado)
    _torso_frente(pn, g, p)
    for lado, item in maos.items():
        if item in ("caneca", "celular"):
            _item_frente(pn, g, item, lado)
            if item == "caneca":
                _mao(pn, g, p, lado)
    rosto_coberto = pose == "maos_rosto"
    if not rosto_coberto:
        for lado, alvo in alvos.items():
            _braco_pose(pn, g, p, lado, alvo)
    _pescoco(pn, g, p)
    _orelhas(pn, g, p)
    _cabeca(pn, g, p)
    _cabelo_frente(pn, g, p)
    _rosto(pn, g, p, expressao, boca, piscando)
    _acessorios_cabeca(pn, g, p)
    if rosto_coberto:
        for lado, alvo in alvos.items():
            _braco_pose(pn, g, p, lado, alvo)
    largura = round((LARG_U + 2 * margem) * altura / ALT_U)
    return img.resize((largura, altura), Image.Resampling.LANCZOS)


@lru_cache(maxsize=1024)
def _cache(chave: str, altura: int, expressao: str, boca: str, piscando: bool, pose: str = "parado",
           margem: float = 0.0) -> Image.Image:
    return _desenhar(Personagem.model_validate(json.loads(chave)), altura, expressao, boca, piscando, pose, margem)


def renderizar(p: Personagem, altura: int, expressao: str | None = None, boca: str = "fechada",
               piscando: bool = False, pose: str = "parado", margem: float = 0.0) -> Image.Image:
    """RGBA figure, `altura` px tall, ((LARG_U + 2*margem)/ALT_U * altura) wide; feet at y = altura * 596/600.

    `pose` bends the arms (POSES); one-arm poses use the viewer-right arm, mirror the image to use the other
    side. Use margem=MARGEM_POSE when arms stretch out, so they are not cut. Cached: copy before drawing on it.
    """
    expressao = expressao or p.expressao
    if expressao not in config.EXPRESSOES:
        raise ValueError(f"expressão desconhecida: {expressao}")
    if boca not in BOCAS:
        raise ValueError(f"boca desconhecida: {boca}")
    if pose not in POSES:
        raise ValueError(f"pose desconhecida: {pose}")
    return _cache(p.model_dump_json(), int(altura), expressao, boca, bool(piscando), pose, float(margem))
