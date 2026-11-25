"""Flat backgrounds and props for the miniseries, in the same clean style as the characters.

Rendered at 2x (2160x3840) so the HyperFrames camera can zoom in without blur. Characters stand with their
feet on CHAO_Y (1x). Props are separate transparent PNGs placed by novela_hf.py.
"""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw

L, A = 1080, 1920
K = 2  # render scale
CHAO_Y = 1560  # feet line (1x) for every setting
TRACO = (38, 40, 50)
LW = 6


def _d(img):
    return ImageDraw.Draw(img)


def _r(d, b, cor, w=LW, raio=0):
    b = [v * K for v in b]
    if raio:
        d.rounded_rectangle(b, radius=raio * K, fill=cor, outline=TRACO, width=w * K // 2)
    else:
        d.rectangle(b, fill=cor, outline=TRACO, width=w * K // 2)


def _p(d, pts, cor, w=LW):
    d.polygon([(x * K, y * K) for x, y in pts], fill=cor, outline=TRACO, width=w * K // 2)


def _e(d, b, cor, w=LW, contorno=True):
    d.ellipse([v * K for v in b], fill=cor, outline=TRACO if contorno else None, width=w * K // 2 if contorno else 0)


def _l(d, pts, cor=TRACO, w=LW):
    d.line([(x * K, y * K) for x, y in pts], fill=cor, width=w * K // 2)


def _ceu(d, chuva: bool):
    if chuva:
        _r(d, (0, 0, L, CHAO_Y - 70), (120, 132, 150), w=0)
        for x, y, s in ((120, 180, 1.2), (520, 120, 1.5), (860, 230, 1.1), (320, 330, 0.9)):
            _e(d, (x - 160 * s, y - 50 * s, x + 160 * s, y + 50 * s), (96, 104, 120), w=0, contorno=False)
    else:
        _r(d, (0, 0, L, CHAO_Y - 70), (176, 220, 245), w=0)
        for x, y, s in ((160, 200, 1.0), (760, 140, 1.3)):
            _e(d, (x - 120 * s, y - 34 * s, x + 120 * s, y + 34 * s), (255, 255, 255), w=0, contorno=False)


def _calcada(d, chuva: bool):
    _r(d, (0, CHAO_Y - 70, L, CHAO_Y + 90), (205, 205, 210) if not chuva else (170, 172, 180))
    for x in range(0, L, 135):
        _l(d, [(x, CHAO_Y - 70), (x - 40, CHAO_Y + 90)], (160, 160, 168), w=3)
    _r(d, (0, CHAO_Y + 90, L, CHAO_Y + 120), (150, 150, 158))
    _r(d, (0, CHAO_Y + 120, L, A), (70, 72, 80) if not chuva else (52, 54, 62), w=0)
    for x in range(40, L, 260):
        _r(d, (x, 1820, x + 140, 1836), (240, 200, 70), w=0)
    if chuva:  # puddles reflecting the sky
        for x, w in ((180, 220), (700, 260)):
            _e(d, (x, CHAO_Y + 170, x + w, CHAO_Y + 210), (96, 110, 130), w=2)


def _cerca_viva(d, chuva: bool):
    verde = (96, 160, 100) if not chuva else (74, 120, 82)
    for x in range(-40, L + 40, 90):
        _e(d, (x, CHAO_Y - 260, x + 130, CHAO_Y - 100), verde, w=4)
    _r(d, (0, CHAO_Y - 180, L, CHAO_Y - 70), verde, w=0)


def _casa(d, chuva: bool):
    _cerca_viva(d, chuva)
    parede = (236, 214, 178) if not chuva else (196, 178, 150)
    _p(d, [(20, 560), (L / 2, 300), (L - 20, 560)], (176, 74, 58) if not chuva else (140, 60, 50))
    _r(d, (70, 540, L - 70, CHAO_Y - 70), parede)
    # window with curtains
    _r(d, (130, 700, 470, 1030), (160, 205, 235))
    _l(d, [(300, 700), (300, 1030)], w=5)
    _l(d, [(130, 865), (470, 865)], w=5)
    _p(d, [(130, 700), (215, 700), (160, 1030), (130, 1030)], (220, 90, 90), w=4)
    _p(d, [(470, 700), (385, 700), (440, 1030), (470, 1030)], (220, 90, 90), w=4)
    _r(d, (110, 1030, 490, 1060), (190, 170, 140))
    # door
    _r(d, (620, 880, 900, CHAO_Y - 70), (138, 86, 52))
    _r(d, (650, 920, 870, 1120), (150, 96, 60), w=4)
    _r(d, (650, 1160, 870, CHAO_Y - 110), (150, 96, 60), w=4)
    _e(d, (840, 1200, 866, 1226), (240, 200, 80), w=3)
    _r(d, (600, CHAO_Y - 90, 920, CHAO_Y - 66), (150, 150, 158))
    _r(d, (720, 800, 800, 850), (250, 250, 250), w=4, raio=8)
    d.text((760 * K, 825 * K), "40", fill=TRACO, anchor="mm", font=_fonte(36 * K))
    # plant
    _r(d, (530, CHAO_Y - 190, 590, CHAO_Y - 70), (200, 110, 70))
    for dx, dy in ((-30, -40), (0, -70), (30, -40), (-10, -20), (20, -15)):
        _e(d, (560 + dx - 30, CHAO_Y - 190 + dy - 30, 560 + dx + 30, CHAO_Y - 190 + dy + 30), (90, 170, 100), w=4)


def _porta_close(d, chuva: bool):
    parede = (236, 214, 178) if not chuva else (196, 178, 150)
    _r(d, (0, 0, L, CHAO_Y - 70), parede, w=0)
    for y in range(120, CHAO_Y - 70, 150):  # subtle siding lines
        _l(d, [(0, y), (L, y)], (220, 196, 160), w=3)
    _r(d, (300, 260, 900, CHAO_Y - 70), (110, 70, 44))  # frame
    _r(d, (340, 300, 860, CHAO_Y - 70), (138, 86, 52))
    for b in ((390, 360, 810, 820), (390, 880, 810, CHAO_Y - 130)):
        _r(d, b, (150, 96, 60), w=5)
    _e(d, (790, 900, 836, 946), (240, 200, 80), w=4)
    _r(d, (520, 170, 680, 240), (250, 250, 250), w=5, raio=10)
    d.text((600 * K, 205 * K), "40", fill=TRACO, anchor="mm", font=_fonte(52 * K))
    _r(d, (90, 520, 190, 640), (60, 60, 70), raio=10)  # wall lamp
    _e(d, (110, 545, 170, 615), (255, 230, 150), w=4)
    _r(d, (0, CHAO_Y - 70, L, CHAO_Y + 90), (205, 205, 210))
    _r(d, (260, CHAO_Y - 90, 940, CHAO_Y - 60), (150, 150, 158))
    _r(d, (0, CHAO_Y + 90, L, A), (70, 72, 80), w=0)


def _interior(d, parede, piso, extra: str):
    _r(d, (0, 0, L, CHAO_Y - 70), parede, w=0)
    _r(d, (0, CHAO_Y - 70, L, A), piso, w=0)
    _l(d, [(0, CHAO_Y - 70), (L, CHAO_Y - 70)], w=6)
    _r(d, (640, 420, 960, 760), (176, 220, 245))  # window
    _l(d, [(800, 420), (800, 760)], w=5)
    if extra == "sala":
        _r(d, (60, CHAO_Y - 330, 560, CHAO_Y - 70), (120, 100, 170), raio=30)
        _r(d, (60, CHAO_Y - 430, 560, CHAO_Y - 300), (140, 120, 190), raio=30)
        _r(d, (130, 480, 470, 720), (250, 250, 250), w=6)  # frame on the wall
        _e(d, (240, 540, 360, 660), (240, 190, 140), w=4)
    elif extra == "cozinha":
        _r(d, (0, CHAO_Y - 420, L, CHAO_Y - 70), (240, 240, 244))
        _r(d, (0, CHAO_Y - 440, L, CHAO_Y - 400), (180, 140, 100))
        for x in range(60, L, 240):
            _r(d, (x, CHAO_Y - 380, x + 200, CHAO_Y - 110), (220, 224, 232), w=4)
        _r(d, (60, 300, 460, 560), (230, 232, 238))
    elif extra == "quarto":
        _r(d, (80, CHAO_Y - 300, 700, CHAO_Y - 70), (250, 250, 250))
        _r(d, (80, CHAO_Y - 300, 700, CHAO_Y - 200), (120, 160, 220))
        _r(d, (60, CHAO_Y - 520, 120, CHAO_Y - 70), (150, 110, 80))
        _r(d, (130, CHAO_Y - 360, 300, CHAO_Y - 290), (255, 255, 255), raio=20)


@lru_cache(maxsize=None)
def _fonte(tam: int):
    from estilo import fonte_black

    return fonte_black(tam)


def fundo(cenario: str, chuva: bool = False) -> Image.Image:
    img = Image.new("RGB", (L * K, A * K), (250, 250, 250))
    d = _d(img)
    if cenario == "calcada_casa":
        _ceu(d, chuva)
        _casa(d, chuva)
        _calcada(d, chuva)
    elif cenario == "porta_casa":
        _porta_close(d, chuva)
    elif cenario == "sala":
        _interior(d, (232, 220, 200), (170, 130, 96), "sala")
    elif cenario == "cozinha":
        _interior(d, (214, 232, 226), (200, 200, 206), "cozinha")
    elif cenario == "quarto":
        _interior(d, (226, 220, 240), (170, 130, 96), "quarto")
    elif cenario == "carro_luxo":
        _ceu(d, chuva)
        _calcada(d, chuva)
    else:
        raise ValueError(f"cenário desconhecido: {cenario}")
    return img


def carro() -> Image.Image:
    """Black luxury sedan, side view, transparent, ~1000x380 at 2x scale."""
    w, h = 1000, 380
    img = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0))
    d = _d(img)
    _p(d, [(30, 250), (60, 170), (250, 150), (360, 60), (680, 60), (800, 150), (960, 175), (980, 260), (960, 300),
           (40, 300)], (34, 36, 44))
    _p(d, [(380, 80), (520, 80), (520, 150), (300, 150)], (150, 190, 220), w=4)
    _p(d, [(540, 80), (670, 80), (760, 150), (540, 150)], (150, 190, 220), w=4)
    _l(d, [(60, 215), (960, 215)], (90, 92, 104), w=4)
    _r(d, (920, 190, 975, 215), (250, 240, 200), w=3)
    for cx in (230, 780):
        _e(d, (cx - 75, 230, cx + 75, 380), (30, 30, 36))
        _e(d, (cx - 40, 265, cx + 40, 345), (180, 182, 192), w=4)
    return img


def malas() -> Image.Image:
    """Two old suitcases, transparent, ~420x300 at 2x."""
    w, h = 420, 300
    img = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0))
    d = _d(img)
    _r(d, (20, 90, 230, 290), (150, 80, 60), raio=18)
    _r(d, (90, 60, 160, 95), (60, 50, 50), raio=10)
    _l(d, [(20, 170), (230, 170)], (110, 60, 46), w=5)
    _r(d, (250, 140, 400, 290), (70, 110, 150), raio=16)
    _r(d, (300, 115, 350, 145), (60, 50, 50), raio=8)
    return img


def estrela() -> Image.Image:
    """Comic impact burst (yellow/orange star), transparent, 360x360 at 2x."""
    import math

    w = 360
    img = Image.new("RGBA", (w * K, w * K), (0, 0, 0, 0))
    d = _d(img)
    for raio, cor in ((170, (244, 142, 62)), (110, (255, 214, 10))):
        pts = []
        for i in range(24):
            r = raio if i % 2 == 0 else raio * 0.55
            a = math.pi * 2 * i / 24
            pts.append((w / 2 + r * math.cos(a), w / 2 + r * math.sin(a)))
        _p(d, pts, cor, w=5)
    return img


def poeira() -> Image.Image:
    """Dust puff at the feet after a move, transparent, 300x300 at 2x."""
    w = 300
    img = Image.new("RGBA", (w * K, w * K), (0, 0, 0, 0))
    d = _d(img)
    for x, y, r in ((90, 200, 55), (150, 185, 70), (215, 205, 50), (120, 230, 40), (190, 235, 42)):
        _e(d, (x - r, y - r, x + r, y + r), (226, 222, 214), w=4)
    return img
