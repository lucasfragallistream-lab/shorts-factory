"""Dynamic captions drawn with Pillow (plan, section 4).

Blocks of 2-4 words, uppercase, heavy font, white with a thick black outline;
the word being spoken is yellow with a short "pop". Everything stays inside the
safe zone: caption centre at ~62% of the height, 90 px side margins, clear of
the bottom 380 px and the right 140 px (TikTok/Reels buttons).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw

import config
from estilo import fonte_black

L, A = config.LARGURA, config.ALTURA
MARGEM_X = 90
RESERVA_DIREITA = 140
RESERVA_INFERIOR = 380
X_MIN, X_MAX = MARGEM_X, L - max(MARGEM_X, RESERVA_DIREITA)
CENTRO_X = (X_MIN + X_MAX) / 2
CENTRO_Y = round(0.62 * A)
CENTRO_Y_GERAL = round(0.36 * A)  # wide shots: above the heads, on the wall
Y_MAX = A - RESERVA_INFERIOR

TAMANHO = 84
TAMANHO_MIN = 52
CONTORNO = 9
ENTRELINHA = 1.12
BRANCO = (255, 255, 255)
AMARELO = (255, 222, 0)
PRETO = (0, 0, 0)
POP_ESCALA = 0.12
POP_DURACAO = 0.12

MAX_PALAVRAS = 4
MIN_PALAVRAS = 2
PAUSA_QUEBRA = 0.22  # a silence this long between words ends a block
SOBRA_FIM = 0.25  # last block of a line stays this long after the last word


@dataclass
class Bloco:
    palavras: list[dict]  # {"texto", "inicio", "fim"} with absolute times
    inicio: float
    fim: float


def _frases(ws: list[dict], texto: str) -> list[list[dict]]:
    """Split words into sentences: by the line's punctuation when tokens match, else by pauses."""
    tokens = texto.split()
    usar_pontuacao = len(tokens) == len(ws)
    frases, atual = [], []
    for j, w in enumerate(ws):
        atual.append(w)
        prox = ws[j + 1] if j + 1 < len(ws) else None
        if usar_pontuacao:
            quebra = tokens[j][-1] in ".!?"
        else:
            quebra = prox is not None and prox["inicio"] - w["fim"] >= PAUSA_QUEBRA
        if prox is None or quebra:
            frases.append(atual)
            atual = []
    return frases


def _dividir(frase: list[dict]) -> list[list[dict]]:
    """Balanced chunks of at most MAX_PALAVRAS (5 -> 3+2, 6 -> 3+3, 7 -> 4+3)."""
    n = len(frase)
    k = -(-n // MAX_PALAVRAS)
    base, extra = divmod(n, k)
    out, i = [], 0
    for g in range(k):
        tam = base + (1 if g < extra else 0)
        out.append(frase[i:i + tam])
        i += tam
    return out


def montar_blocos(falas: list[dict]) -> list[Bloco]:
    """Split each narrated segment into sentence-aligned blocks of 2-4 words (a one-word sentence stays alone)."""
    blocos: list[Bloco] = []
    for k, fala in enumerate(falas):
        ws = [w for w in fala["palavras"] if w["texto"].strip()]
        grupos = [g for frase in _frases(ws, fala.get("texto", "")) for g in _dividir(frase)]
        limite = falas[k + 1]["inicio"] if k + 1 < len(falas) else math.inf
        for g, grupo in enumerate(grupos):
            fim = grupos[g + 1][0]["inicio"] if g + 1 < len(grupos) else min(grupo[-1]["fim"] + SOBRA_FIM, limite)
            blocos.append(Bloco(grupo, grupo[0]["inicio"], fim))
    return blocos


def bloco_em(blocos: list[Bloco], t: float) -> Bloco | None:
    for b in blocos:
        if b.inicio <= t < b.fim:
            return b
    return None


def palavra_ativa(bloco: Bloco, t: float) -> int | None:
    for i, w in enumerate(bloco.palavras):
        prox = bloco.palavras[i + 1]["inicio"] if i + 1 < len(bloco.palavras) else w["fim"]
        if w["inicio"] <= t < max(prox, w["fim"]):
            return i
    return None


def _linhas(textos: list[str], tamanho: int) -> list[list[int]] | None:
    """Greedy wrap of word indices into lines no wider than the safe zone."""
    f = fonte_black(tamanho)
    largura_max = X_MAX - X_MIN - 2 * CONTORNO
    espaco = f.getlength(" ") * 1.4
    linhas, atual, larg = [], [], 0.0
    for i, w in enumerate(textos):
        lw = f.getlength(w)
        if lw > largura_max:
            return None
        nova = lw if not atual else larg + espaco + lw
        if atual and nova > largura_max:
            linhas.append(atual)
            atual, larg = [i], lw
        else:
            atual.append(i)
            larg = nova
    if atual:
        linhas.append(atual)
    return linhas


def layout(textos: list[str]) -> tuple[int, list[list[int]]]:
    tamanho = TAMANHO
    while tamanho > TAMANHO_MIN:
        linhas = _linhas(textos, tamanho)
        if linhas is not None and len(linhas) <= 2:
            return tamanho, linhas
        tamanho -= 6
    return TAMANHO_MIN, _linhas(textos, TAMANHO_MIN) or [list(range(len(textos)))]


def desenhar_bloco(img: Image.Image, bloco: Bloco, t: float, centro_y: float = CENTRO_Y) -> None:
    textos = [w["texto"].upper() for w in bloco.palavras]
    tamanho, linhas = layout(textos)
    f = fonte_black(tamanho)
    espaco = f.getlength(" ") * 1.4
    alt_linha = tamanho * ENTRELINHA
    y0 = centro_y - alt_linha * (len(linhas) - 1) / 2
    y0 = min(y0, Y_MAX - tamanho / 2 - alt_linha * (len(linhas) - 1))  # move the whole block, never squeeze lines
    ativa = palavra_ativa(bloco, t)
    d = ImageDraw.Draw(img)
    depois = []
    for n, linha in enumerate(linhas):
        larguras = [f.getlength(textos[i]) for i in linha]
        x = CENTRO_X - (sum(larguras) + espaco * (len(linha) - 1)) / 2
        y = min(y0 + n * alt_linha, Y_MAX - tamanho / 2)
        for i, lw in zip(linha, larguras):
            cx = x + lw / 2
            if i == ativa:
                idade = t - bloco.palavras[i]["inicio"]
                escala = 1 + POP_ESCALA * max(0.0, 1 - idade / POP_DURACAO)
                depois.append((cx, y, textos[i], round(tamanho * escala)))
            else:
                d.text((cx, y), textos[i], font=f, fill=BRANCO, stroke_width=CONTORNO, stroke_fill=PRETO,
                       anchor="mm")
            x += lw + espaco
    for cx, y, txt, tam in depois:  # active word on top, so its pop overlaps neighbours
        d.text((cx, y), txt, font=fonte_black(tam), fill=AMARELO, stroke_width=CONTORNO + 1, stroke_fill=PRETO,
               anchor="mm")


def desenhar_gancho(img: Image.Image, texto: str, t: float, duracao: float = 2.0) -> None:
    """Big hook text for the first seconds: pops in, slightly tilted, upper third."""
    if t >= duracao or not texto:
        return
    entrada = min(1.0, t / 0.2)
    escala = 0.6 + 0.4 * (1 + 2.2 * (entrada - 1) ** 3 + 1.2 * (entrada - 1) ** 2)  # ease-out-back
    tamanho = 118
    palavras = texto.upper().split()
    while True:
        f = fonte_black(tamanho)
        linhas, atual = [], ""
        for w in palavras:
            teste = f"{atual} {w}".strip()
            if f.getlength(teste) > X_MAX - X_MIN - 40 and atual:
                linhas.append(atual)
                atual = w
            else:
                atual = teste
        linhas.append(atual)
        if max(f.getlength(li) for li in linhas) <= X_MAX - X_MIN - 40 or tamanho <= 60:
            break
        tamanho -= 8
    alt = tamanho * 1.1
    camada = Image.new("RGBA", (X_MAX - X_MIN, int(alt * len(linhas) + 60)), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    for n, li in enumerate(linhas):
        d.text((camada.width / 2, 30 + alt * (n + 0.5)), li, font=f, fill=AMARELO, stroke_width=12,
               stroke_fill=PRETO, anchor="mm")
    w, h = max(1, round(camada.width * escala)), max(1, round(camada.height * escala))
    camada = camada.resize((w, h), Image.Resampling.BILINEAR).rotate(4, expand=True,
                                                                     resample=Image.Resampling.BICUBIC)
    cx, cy = CENTRO_X, round(0.27 * A)
    img.paste(camada, (round(cx - camada.width / 2), round(cy - camada.height / 2)), camada)


class Legendas:
    def __init__(self, timeline: dict):
        self.blocos = montar_blocos(timeline["segmentos"])
        self.gancho = timeline.get("gancho_visual", "")

    def desenhar(self, img: Image.Image, t: float, centro_y: float = CENTRO_Y) -> None:
        desenhar_gancho(img, self.gancho, t)
        b = bloco_em(self.blocos, t)
        if b is not None and t >= 0:
            desenhar_bloco(img, b, t, centro_y)
