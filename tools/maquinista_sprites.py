"""2D sprites (flat style, dark outline) for the "Você é o Maquinista" 3D world.

Usage: python tools/maquinista_sprites.py motion/trolley/public/ep2/sprites [ep1|ep2]
People come from figure_renderer (one PNG per expression/mouth/pose); animals and props are drawn here.
All PNGs are transparent; people share the figure canvas (feet at 596/600): 340x600 standing still, 580x600 with
MARGEM_POSE when the arms move (gestures). Faces that get extreme close-ups are rendered at 2x (ALT_HD).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import figure_renderer as fr  # noqa: E402
from estilo import fonte_black  # noqa: E402
from schemas import Personagem  # noqa: E402

TRACO = (38, 40, 50, 255)
K = 2  # supersampling
ALT = 1200
ALT_HD = 2400  # eye/moustache close-ups in the countdown montage

ELENCO = {
    "maquinista": (Personagem(idade="adulto", sexo="masculino", pele="media", cabelo="curto", cor_cabelo="castanho",
                              roupa="camisa", cor_roupa="azul", acessorios=["bigode", "bone"]),
                   ["preocupado", "chocado", "raiva", "triste"]),
    "helena": (Personagem(idade="adulto", sexo="feminino", pele="clara", cabelo="comprido", cor_cabelo="castanho",
                          roupa="social", cor_roupa="branco", acessorios=["oculos", "colar"]),
               ["preocupado", "feliz", "chocado"]),
    "cida": (Personagem(idade="idoso", sexo="feminino", pele="morena", cabelo="coque", cor_cabelo="branco",
                        roupa="vestido", cor_roupa="roxo", acessorios=["oculos"]),
             ["triste", "chocado"]),
}


def _d(img):
    return ImageDraw.Draw(img)


def _e(d, b, cor, w=6):
    d.ellipse([v * K for v in b], fill=cor, outline=TRACO, width=w * K)


def _fim(img: Image.Image) -> Image.Image:
    return img.resize((img.width // K, img.height // K), Image.Resampling.LANCZOS)


def filhote(tom: float, boca: str) -> Image.Image:
    """Sitting golden puppy facing the viewer, 400x400."""
    img = Image.new("RGBA", (400 * K, 400 * K), (0, 0, 0, 0))
    d = _d(img)
    c = lambda r, g, b: (min(255, int(r * tom)), min(255, int(g * tom)), min(255, int(b * tom)), 255)  # noqa: E731
    pelo, escuro, creme = c(232, 172, 92), c(204, 140, 64), (252, 230, 186, 255)
    _e(d, (110, 200, 290, 392), pelo)
    _e(d, (120, 350, 185, 395), creme)
    _e(d, (215, 350, 280, 395), creme)
    _e(d, (150, 250, 250, 360), creme, 4)
    _e(d, (62, 96, 140, 250), escuro)
    _e(d, (260, 96, 338, 250), escuro)
    _e(d, (92, 50, 308, 262), pelo)
    _e(d, (150, 150, 250, 232), creme, 4)
    _e(d, (182, 152, 218, 178), (40, 34, 36, 255), 3)
    for x in (152, 248):
        _e(d, (x - 15, 112, x + 15, 142), (30, 26, 30, 255), 2)
        d.ellipse([(x - 5) * K, 117 * K, (x + 3) * K, 125 * K], fill=(255, 255, 255, 255))
    if boca == "aberta":
        _e(d, (172, 186, 228, 238), (120, 30, 40, 255), 4)
        _e(d, (184, 212, 216, 240), (240, 110, 130, 255), 3)
    else:
        d.arc([174 * K, 172 * K, 202 * K, 200 * K], 20, 160, fill=TRACO, width=5 * K)
        d.arc([198 * K, 172 * K, 226 * K, 200 * K], 20, 160, fill=TRACO, width=5 * K)
    return _fim(img)


def panda() -> Image.Image:
    """Sleeping baby panda, 420x380."""
    img = Image.new("RGBA", (420 * K, 380 * K), (0, 0, 0, 0))
    d = _d(img)
    preto, branco = (36, 36, 44, 255), (250, 250, 250, 255)
    _e(d, (70, 170, 350, 370), branco)
    _e(d, (60, 260, 150, 360), preto)
    _e(d, (270, 260, 360, 360), preto)
    _e(d, (50, 190, 130, 280), preto)
    _e(d, (290, 190, 370, 280), preto)
    _e(d, (100, 20, 160, 80), preto)
    _e(d, (260, 20, 320, 80), preto)
    _e(d, (100, 30, 320, 230), branco)
    for x0 in (138, 232):
        d.ellipse([x0 * K, 100 * K, (x0 + 52) * K, 150 * K], fill=preto)
        d.arc([(x0 + 10) * K, 112 * K, (x0 + 42) * K, 136 * K], 20, 160, fill=branco, width=5 * K)
    _e(d, (194, 150, 226, 172), preto, 3)
    d.arc([186 * K, 160 * K, 234 * K, 196 * K], 30, 150, fill=TRACO, width=5 * K)
    f = fonte_black(44 * K)
    for i, (x, y) in enumerate(((330, 40), (360, 0))):
        d.text((x * K, y * K), "z", font=f, fill=(90, 120, 200, 255), stroke_width=4 * K, stroke_fill=(255, 255, 255, 255))
    return _fim(img)


def frasco() -> Image.Image:
    """Glowing cure vial with halo, 300x300."""
    img = Image.new("RGBA", (300 * K, 300 * K), (0, 0, 0, 0))
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    _d(halo).ellipse([40 * K, 40 * K, 260 * K, 260 * K], fill=(120, 255, 150, 150))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(34 * K)))
    d = _d(img)
    d.rounded_rectangle([120 * K, 70 * K, 180 * K, 250 * K], radius=28 * K, fill=(215, 240, 250, 230), outline=TRACO,
                        width=6 * K)
    d.rounded_rectangle([126 * K, 140 * K, 174 * K, 244 * K], radius=22 * K, fill=(80, 230, 120, 255))
    d.rectangle([128 * K, 44 * K, 172 * K, 76 * K], fill=(170, 110, 70, 255), outline=TRACO, width=5 * K)
    for x, y in ((140, 170), (155, 200), (146, 222)):
        d.ellipse([x * K, y * K, (x + 10) * K, (y + 10) * K], fill=(220, 255, 230, 255))
    return _fim(img)


def gota() -> Image.Image:
    img = Image.new("RGBA", (80 * K, 120 * K), (0, 0, 0, 0))
    d = _d(img)
    d.polygon([(40 * K, 8 * K), (66 * K, 74 * K), (14 * K, 74 * K)], fill=(140, 200, 255, 255))
    _e(d, (14, 50, 66, 110), (140, 200, 255, 255), 4)
    d.line([(40 * K, 10 * K), (66 * K, 74 * K)], fill=TRACO, width=4 * K)
    d.line([(40 * K, 10 * K), (14 * K, 74 * K)], fill=TRACO, width=4 * K)
    d.ellipse([28 * K, 66 * K, 40 * K, 80 * K], fill=(240, 250, 255, 255))
    return _fim(img)


def placa(letra: str, cor: tuple) -> Image.Image:
    """Track sign board (letter inside the world, kit rule: text lives in the world), 512x512."""
    img = Image.new("RGBA", (512 * K, 512 * K), (0, 0, 0, 0))
    d = _d(img)
    d.rounded_rectangle([16 * K, 16 * K, 496 * K, 496 * K], radius=70 * K, fill=cor + (255,), outline=TRACO, width=16 * K)
    d.rounded_rectangle([46 * K, 46 * K, 466 * K, 466 * K], radius=50 * K, outline=(255, 255, 255, 255), width=10 * K)
    d.text((256 * K, 270 * K), letra, font=fonte_black(360 * K), fill=(255, 255, 255, 255), anchor="mm",
           stroke_width=14 * K, stroke_fill=TRACO)
    return _fim(img)


VOVOS = {  # ep. 2: five grandpas playing dominoes (the fifth is the father, drawn apart)
    "vovo1": Personagem(idade="idoso", sexo="masculino", pele="clara", cabelo="careca", cor_cabelo="grisalho",
                        roupa="camisa", cor_roupa="verde", acessorios=["oculos"]),
    "vovo2": Personagem(idade="idoso", sexo="masculino", pele="negra", cabelo="curto", cor_cabelo="branco",
                        roupa="camiseta", cor_roupa="amarelo", acessorios=["barba"]),
    "vovo3": Personagem(idade="idoso", sexo="masculino", pele="morena", cabelo="careca", cor_cabelo="grisalho",
                        roupa="camisa", cor_roupa="vermelho", acessorios=["bone"]),
    "vovo4": Personagem(idade="idoso", sexo="masculino", pele="media", cabelo="liso", cor_cabelo="branco",
                        roupa="jaqueta", cor_roupa="cinza", acessorios=["oculos"]),
}
PAI = Personagem(idade="idoso", sexo="masculino", pele="media", cabelo="curto", cor_cabelo="grisalho",
                 roupa="camisa", cor_roupa="laranja", acessorios=["bigode"])


def pacoca(boca: str, rabo: int) -> Image.Image:
    """Paçoca, a sitting caramel mutt facing the viewer, red collar with a gold tag, tail wagging (2 frames), 420x460."""
    img = Image.new("RGBA", (420 * K, 460 * K), (0, 0, 0, 0))
    d = _d(img)
    pelo, escuro, creme = (214, 150, 72, 255), (178, 112, 46, 255), (248, 222, 176, 255)
    w = 24 * K
    pts = [(300, 400), (350, 360), (372, 300), (360, 250)] if rabo else [(300, 400), (352, 392), (396, 352), (404, 300)]
    d.line([(x * K, y * K) for x, y in pts], fill=TRACO, width=w + 12 * K, joint="curve")
    d.line([(x * K, y * K) for x, y in pts], fill=pelo, width=w, joint="curve")
    _e(d, (112, 220, 308, 448), pelo)
    _e(d, (160, 268, 260, 420), creme, 4)
    for x0 in (150, 232):
        d.rounded_rectangle([x0 * K, 360 * K, (x0 + 40) * K, 452 * K], radius=18 * K, fill=pelo, outline=TRACO, width=6 * K)
        _e(d, (x0 - 6, 424, x0 + 46, 456), creme, 5)
    d.polygon([(118 * K, 92 * K), (70 * K, 150 * K), (96 * K, 230 * K), (150 * K, 120 * K)], fill=escuro)
    d.line([(118 * K, 92 * K), (70 * K, 150 * K), (96 * K, 230 * K)], fill=TRACO, width=6 * K)
    d.polygon([(290 * K, 100 * K), (330 * K, 30 * K), (348 * K, 130 * K)], fill=escuro)
    d.line([(290 * K, 100 * K), (330 * K, 30 * K), (348 * K, 130 * K)], fill=TRACO, width=6 * K)
    _e(d, (108, 62, 312, 256), pelo)
    _e(d, (160, 150, 260, 244), creme, 4)
    _e(d, (192, 150, 228, 178), (40, 30, 30, 255), 3)
    for x in (162, 258):
        _e(d, (x - 16, 112, x + 16, 146), (30, 24, 26, 255), 2)
        d.ellipse([(x - 6) * K, 118 * K, (x + 3) * K, 127 * K], fill=(255, 255, 255, 255))
        d.arc([(x - 22) * K, 92 * K, (x + 18) * K, 116 * K], 200, 330, fill=TRACO, width=5 * K)
    if boca == "aberta":
        _e(d, (180, 190, 240, 240), (120, 30, 40, 255), 4)
        _e(d, (192, 214, 228, 262), (240, 110, 130, 255), 3)
    else:
        d.arc([178 * K, 176 * K, 210 * K, 206 * K], 20, 160, fill=TRACO, width=5 * K)
        d.arc([206 * K, 176 * K, 238 * K, 206 * K], 20, 160, fill=TRACO, width=5 * K)
    d.rounded_rectangle([136 * K, 240 * K, 284 * K, 266 * K], radius=12 * K, fill=(214, 38, 46, 255), outline=TRACO,
                        width=5 * K)
    _e(d, (196, 258, 224, 286), (248, 200, 60, 255), 4)
    return _fim(img)


def bilhete() -> Image.Image:
    """The winning lottery ticket (text lives in the world), with a golden halo, 600x380."""
    img = Image.new("RGBA", (600 * K, 380 * K), (0, 0, 0, 0))
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    _d(halo).rounded_rectangle([30 * K, 30 * K, 570 * K, 350 * K], radius=60 * K, fill=(255, 220, 90, 170))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(26 * K)))
    d = _d(img)
    d.rounded_rectangle([70 * K, 70 * K, 530 * K, 310 * K], radius=22 * K, fill=(252, 214, 72, 255), outline=TRACO,
                        width=8 * K)
    d.rounded_rectangle([88 * K, 88 * K, 512 * K, 292 * K], radius=14 * K, outline=(214, 150, 30, 255), width=5 * K)
    d.text((300 * K, 132 * K), "BILHETE PREMIADO", font=fonte_black(40 * K), fill=(150, 40, 30, 255), anchor="mm")
    d.text((300 * K, 210 * K), "R$ 600.000.000", font=fonte_black(64 * K), fill=(255, 255, 255, 255), anchor="mm",
           stroke_width=7 * K, stroke_fill=TRACO)
    for x in range(110, 500, 26):
        d.line([(x * K, 262 * K), (x * K, 280 * K)], fill=TRACO, width=(4 if x % 52 else 7) * K)
    return _fim(img)


def mao() -> Image.Image:
    """A fist gripping the lever knob (driver's skin, blue sleeve), 320x320."""
    img = Image.new("RGBA", (320 * K, 320 * K), (0, 0, 0, 0))
    d = _d(img)
    pele = fr.PELE["media"] + (255,)
    d.rounded_rectangle([60 * K, 210 * K, 230 * K, 316 * K], radius=24 * K, fill=(62, 138, 214, 255), outline=TRACO,
                        width=7 * K)
    _e(d, (40, 70, 270, 250), pele, 7)
    for i in range(4):
        y = 92 + i * 38
        _e(d, (200, y, 292, y + 46), pele, 6)
    _e(d, (52, 40, 170, 132), pele, 7)
    for i in range(3):
        y = 130 + i * 38
        d.arc([150 * K, (y - 10) * K, 230 * K, (y + 26) * K], 300, 60, fill=TRACO, width=5 * K)
    return _fim(img)


def saco_pao() -> Image.Image:
    """Brown paper bag with two baguettes sticking out, 300x420."""
    img = Image.new("RGBA", (300 * K, 420 * K), (0, 0, 0, 0))
    for x0, rot in ((96, -10), (150, 8)):
        b = Image.new("RGBA", (90 * K, 300 * K), (0, 0, 0, 0))
        bd = _d(b)
        bd.rounded_rectangle([10 * K, 6 * K, 80 * K, 294 * K], radius=34 * K, fill=(226, 172, 96, 255), outline=TRACO,
                             width=6 * K)
        for y in (60, 120, 180):
            bd.line([(26 * K, y * K), (62 * K, (y + 26) * K)], fill=(160, 100, 50, 255), width=6 * K)
        b = b.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
        img.alpha_composite(b, (x0 * K - b.width // 2 + 45 * K, 0))
    d = _d(img)
    canto = [(46 * K, 150 * K), (254 * K, 150 * K), (270 * K, 410 * K), (30 * K, 410 * K)]
    d.polygon(canto, fill=(196, 150, 96, 255))
    d.line(canto + [canto[0]], fill=TRACO, width=7 * K)
    d.line([(50 * K, 176 * K), (250 * K, 176 * K)], fill=(150, 108, 64, 255), width=5 * K)
    d.text((150 * K, 290 * K), "PÃO", font=fonte_black(54 * K), fill=(120, 70, 40, 255), anchor="mm")
    return _fim(img)


def _com_saco(fig: Image.Image, mao_xy: tuple[float, float], alt_m: float = 0.55) -> Image.Image:
    """Hang the bread bag from a hand (mao_xy as fractions of the canvas); alt_m = bag height in metres (figure 1.95 m)."""
    fig = fig.copy()
    s = saco_pao()
    h = int(fig.height * alt_m / 1.95)
    s = s.resize((int(s.width * h / s.height), h), Image.Resampling.LANCZOS)
    x, y = int(mao_xy[0] * fig.width - s.width / 2), int(mao_xy[1] * fig.height - h * 0.18)
    fig.alpha_composite(s, (max(0, min(fig.width - s.width, x)), y))
    return fig


def ep2(destino: Path):
    p, exprs = ELENCO["maquinista"]
    for e in exprs:
        for b in ("fechada", "aberta"):
            fr.renderizar(p, ALT_HD, e, b).save(destino / f"maquinista_{e}_{b}.png")
    for nome, pv in VOVOS.items():
        for b in ("fechada", "aberta"):
            fr.renderizar(pv, ALT, "feliz", b).save(destino / f"{nome}_feliz_{b}.png")
    fr.renderizar(VOVOS["vovo1"], ALT, "feliz", "aberta", pose="bracos_cima", margem=fr.MARGEM_POSE).save(
        destino / "vovo1_bati.png")
    for b in ("fechada", "aberta"):
        fig = fr.renderizar(PAI, ALT_HD, "feliz", b, pose="parado", margem=fr.MARGEM_POSE)
        _com_saco(fig, (0.633, 0.70)).save(destino / f"pai_feliz_{b}.png")
        fig = fr.renderizar(PAI, ALT_HD, "feliz", b, pose="estende", margem=fr.MARGEM_POSE)
        _com_saco(fig, (0.945, 0.44)).save(destino / f"pai_pao_{b}.png")
    for b in ("fechada", "aberta"):
        for r in (0, 1):
            pacoca(b, r).save(destino / f"pacoca_{b}_{r}.png")
    bilhete().save(destino / "bilhete.png")
    mao().save(destino / "mao.png")
    gota().save(destino / "gota.png")
    placa("A", (48, 132, 230)).save(destino / "placa_a.png")
    placa("B", (230, 64, 84)).save(destino / "placa_b.png")


DOUTORA = Personagem(idade="adulto", sexo="feminino", pele="negra", cabelo="coque", cor_cabelo="preto",
                     roupa="social", cor_roupa="branco", acessorios=["oculos"])  # white coat = lab coat


def maleta() -> Image.Image:
    """Open silver case on the track, the last zombie vaccine glowing blue in the foam, 600x460."""
    img = Image.new("RGBA", (600 * K, 460 * K), (0, 0, 0, 0))
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    _d(halo).ellipse([170 * K, 40 * K, 430 * K, 300 * K], fill=(90, 190, 255, 190))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(40 * K)))
    d = _d(img)
    d.polygon([(110 * K, 40 * K), (490 * K, 40 * K), (520 * K, 200 * K), (80 * K, 200 * K)], fill=(176, 184, 196, 255))
    d.line([(110 * K, 40 * K), (490 * K, 40 * K), (520 * K, 200 * K), (80 * K, 200 * K), (110 * K, 40 * K)], fill=TRACO,
           width=8 * K)
    d.rounded_rectangle([200 * K, 70 * K, 400 * K, 130 * K], radius=12 * K, fill=(255, 255, 255, 255), outline=TRACO,
                        width=5 * K)
    d.text((300 * K, 101 * K), "VACINA", font=fonte_black(40 * K), fill=(30, 110, 220, 255), anchor="mm")
    d.rounded_rectangle([60 * K, 200 * K, 540 * K, 440 * K], radius=26 * K, fill=(150, 158, 172, 255), outline=TRACO,
                        width=8 * K)
    d.rounded_rectangle([96 * K, 222 * K, 504 * K, 300 * K], radius=16 * K, fill=(58, 62, 74, 255))
    for x in (160, 440):
        d.rounded_rectangle([(x - 40) * K, 380 * K, (x + 40) * K, 404 * K], radius=8 * K, fill=(110, 116, 130, 255),
                            outline=TRACO, width=4 * K)
    d.rounded_rectangle([272 * K, 150 * K, 328 * K, 300 * K], radius=24 * K, fill=(220, 240, 252, 235), outline=TRACO,
                        width=6 * K)
    d.rounded_rectangle([278 * K, 200 * K, 322 * K, 294 * K], radius=20 * K, fill=(60, 170, 255, 255))
    d.rectangle([280 * K, 126 * K, 320 * K, 156 * K], fill=(214, 60, 70, 255), outline=TRACO, width=5 * K)
    for x, y in ((290, 222), (304, 250), (292, 270)):
        d.ellipse([x * K, y * K, (x + 9) * K, (y + 9) * K], fill=(230, 248, 255, 255))
    return _fim(img)


def braco(mordido: bool) -> Image.Image:
    """The driver's forearm in close-up (horizontal, hand on the right), 700x380. mordido: sleeve rolled up, a bite
    mark (purple, no blood) and green veins spreading from it."""
    img = Image.new("RGBA", (700 * K, 380 * K), (0, 0, 0, 0))
    d = _d(img)
    pele = fr.PELE["media"] + (255,)
    azul = (62, 138, 214, 255)
    d.rounded_rectangle([20 * K, 110 * K, 560 * K, 290 * K], radius=80 * K, fill=pele, outline=TRACO, width=8 * K)
    _e(d, (500, 96, 680, 300), pele, 8)  # fist
    for i in range(3):
        d.arc([600 * K, (130 + i * 44) * K, 676 * K, (176 + i * 44) * K], 300, 60, fill=TRACO, width=5 * K)
    if not mordido:
        d.rounded_rectangle([10 * K, 96 * K, 470 * K, 304 * K], radius=70 * K, fill=azul, outline=TRACO, width=8 * K)
        d.rounded_rectangle([430 * K, 92 * K, 486 * K, 308 * K], radius=20 * K, fill=(48, 112, 180, 255), outline=TRACO,
                            width=7 * K)
        return _fim(img)
    for xs, ys in (((300, 230, 160, 110), (170, 140, 120, 96)), ((300, 220, 150), (240, 262, 286)),
                   ((330, 400, 450), (150, 128, 116))):
        d.line([(x * K, y * K) for x, y in zip(xs, ys)], fill=(96, 170, 90, 255), width=9 * K, joint="curve")
    d.rounded_rectangle([10 * K, 92 * K, 120 * K, 308 * K], radius=40 * K, fill=azul, outline=TRACO, width=8 * K)
    d.rounded_rectangle([96 * K, 86 * K, 150 * K, 314 * K], radius=22 * K, fill=(48, 112, 180, 255), outline=TRACO, width=7 * K)
    _e(d, (250, 150, 390, 250), (214, 150, 150, 255), 0)  # irritated skin
    for i in range(12):  # the bite: two arcs of teeth marks
        a = math.pi * (i % 6) / 5
        cy = 172 if i < 6 else 228
        x = 320 + 52 * math.cos(math.pi - a)
        y = cy + (14 if i < 6 else -14) * math.sin(a)
        d.ellipse([(x - 9) * K, (y - 7) * K, (x + 9) * K, (y + 7) * K], fill=(120, 40, 110, 255))
    return _fim(img)


def pano() -> Image.Image:
    """The corner of the white lab coat caught under the rail, 360x200."""
    img = Image.new("RGBA", (360 * K, 200 * K), (0, 0, 0, 0))
    d = _d(img)
    pts = [(20, 40), (300, 10), (345, 170), (60, 190)]
    d.polygon([(x * K, y * K) for x, y in pts], fill=(246, 246, 250, 255))
    d.line([(x * K, y * K) for x, y in pts + [pts[0]]], fill=TRACO, width=7 * K)
    for x in (120, 200):
        d.line([(x * K, 30 * K), ((x + 30) * K, 180 * K)], fill=(200, 204, 214, 255), width=6 * K)
    return _fim(img)


def ep3(destino: Path):
    p, exprs = ELENCO["maquinista"]
    for e in exprs:
        for b in ("fechada", "aberta"):
            fr.renderizar(p, ALT_HD, e, b).save(destino / f"maquinista_{e}_{b}.png")
    for e, bocas in (("triste", ("fechada", "aberta")), ("raiva", ("aberta",)), ("chocado", ("fechada",))):
        for b in bocas:
            fr.renderizar(DOUTORA, ALT_HD, e, b, pose="estende", margem=fr.MARGEM_POSE).save(destino / f"doutora_{e}_{b}.png")
    maleta().save(destino / "maleta.png")
    braco(False).save(destino / "braco_manga.png")
    braco(True).save(destino / "braco_mordida.png")
    pano().save(destino / "pano.png")
    mao().save(destino / "mao.png")
    gota().save(destino / "gota.png")
    placa("A", (48, 132, 230)).save(destino / "placa_a.png")
    placa("B", (230, 64, 84)).save(destino / "placa_b.png")


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    destino = Path(argv[0])
    destino.mkdir(parents=True, exist_ok=True)
    modo = argv[1] if len(argv) > 1 else "ep2"
    if modo in ("ep2", "ep3"):
        (ep2 if modo == "ep2" else ep3)(destino)
        print(f"sprites em {destino}: {len(list(destino.glob('*.png')))}")
        return 0
    for nome, (p, exprs) in ELENCO.items():
        for e in exprs:
            for b in ("fechada", "aberta"):
                fr.renderizar(p, ALT, e, b).save(destino / f"{nome}_{e}_{b}.png")
    for i, tom in enumerate((1.0, 0.9, 1.08)):
        for b in ("fechada", "aberta"):
            filhote(tom, b).save(destino / f"filhote{i}_{b}.png")
    panda().save(destino / "panda.png")
    frasco().save(destino / "frasco.png")
    gota().save(destino / "gota.png")
    placa("A", (48, 132, 230)).save(destino / "placa_a.png")
    placa("B", (230, 64, 84)).save(destino / "placa_b.png")
    print(f"sprites em {destino}: {len(list(destino.glob('*.png')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
