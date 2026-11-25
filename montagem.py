"""Ranking montage (phase R4): camera with motion, emoji pops, CTA card, captions, title and label.

Timeline v2 (voice_engine.gerar_audio) drives everything. Segments:
    abertura   -> hook: the camera starts close on the hidden last item ("?") and pulls out to the
                  wide shot; emojis of the opening pop in the middle of the stage
    item i     -> camera eases into item i; its tag turns blue and is revealed; the figure hops and
                  bounces with the voice; each `visual` (emoji tied to a spoken word) pops next to the
                  figure while the camera punches in on its face and releases (zoom in / out rhythm)
    cta        -> wide shot, stage dimmed, "CURTE / COMENTA / SEGUE" stickers pop in sequence
    fechamento -> wide shot, every tag revealed, closing emojis
The stage is rendered at ZOOM_MAX and cropped, so zooming never upscales pixels.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

import config
import emoji_renderer as er
import layout_renderer as lr
from captions import Legendas
from estilo import fonte_black
from schemas import Ranking

L, A = config.LARGURA, config.ALTURA
BANDA_H = lr.PALCO_Y1 - lr.PALCO_Y0
ZOOM_MAX = 1.6
ZOOM_ITEM = 1.28
ZOOM_ROSTO = 1.55  # punch-in on the face while an emoji is on screen
TRANSICAO = 0.45  # s, camera ease between segments
GANCHO = 1.4  # s, opening pull-out from the hidden last item
ATAQUE, SOLTA = 0.18, 0.45  # s, punch-in attack / release
POP = 0.22  # s, pop-in of title / label / stickers
EVENTO_MIN, EVENTO_MAX = 0.9, 1.8  # s on screen per emoji
ADESIVO = 300  # px, emoji sticker size
PISCA_FRAMES = 4
OPACIDADE_FUNDO = 0.38
PROGRESSO_Y = 440
GANCHO_ROSTO = 0.9  # s: first frames are an extreme close-up on a face + giant title
FOTO_INICIO, FOTO_GRANDE = 0.7, 2.0  # s after item start: photo pops in, stays big, then to a corner
SLAM = 0.75  # s the item number stays slammed on screen
SLAM_Y = 760
FLASH = 0.12
TREMIDA = 0.35  # segmented progress bar, just under the title banner  # other figures while an item is narrated
CTA = (("👍", "CURTE"), ("💬", "COMENTA"), ("➕", "SEGUE"))


def _ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _ease_back(x: float) -> float:
    """0 -> 1 with a small overshoot (ease-out-back)."""
    x = min(max(x, 0.0), 1.0)
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _norm(txt: str) -> str:
    txt = unicodedata.normalize("NFD", txt.lower())
    return "".join(c for c in txt if c.isalnum() and not unicodedata.combining(c))


@dataclass
class Camera:
    z: float  # 1 = wide shot
    cx: float  # center in frame px (x)
    cy: float  # center in frame px (y, inside the stage band)

    def misturar(self, outra: "Camera", k: float) -> "Camera":
        return Camera(self.z + (outra.z - self.z) * k, self.cx + (outra.cx - self.cx) * k,
                      self.cy + (outra.cy - self.cy) * k)


@dataclass
class Evento:
    """An emoji on screen (or a camera beat without emoji when `emoji` is empty)."""
    inicio: float
    fim: float
    emoji: str
    tipo: str  # segment type
    item: int | None


class Montagem:
    def __init__(self, ranking: Ranking, timeline: dict, revelar_progressivo: bool = True, seed: int = 0,
                 fotos: dict[int, Path] | None = None):
        self.r = ranking
        self.fotos = fotos or {}  # item index -> real photo (imagens.py)
        self.n = len(ranking.itens)
        self.tl = timeline
        self.fps = timeline["fps"]
        self.n_frames = timeline["frames"]
        self.duracao = timeline["duracao"]
        self.palco = lr.Palco(ranking, escala=ZOOM_MAX)
        self.palco1 = lr.Palco(ranking)  # 1x positions
        self.legendas = Legendas(timeline)
        self.revelar = revelar_progressivo
        self.item_atual = timeline["item_atual"]
        self.energia = timeline["energia"]
        self.segs = timeline["segmentos"]
        self.inicio_item = {s["item"]: s["inicio"] for s in self.segs if s["tipo"] == "item"}
        self.fim_item = {s["item"]: s["fim"] for s in self.segs if s["tipo"] == "item"}
        self.fechamento = next((s["inicio"] for s in self.segs if s["tipo"] == "fechamento"), self.duracao)
        self.cta = next(((s["inicio"], s["fim"]) for s in self.segs if s["tipo"] == "cta"), None)
        self.eventos = self._montar_eventos()
        self._janela = (0.0, 0.0, 1.0, 1.0)
        self._lugares: dict[tuple, tuple[float, float]] = {}
        self.piscadas = []
        for i in range(self.n):  # deterministic blink schedule per figure
            marcas, f, k = set(), int(self.fps * (0.8 + 0.37 * i + (seed % 7) * 0.1)), 0
            while f < self.n_frames:
                marcas.update(range(f, f + PISCA_FRAMES))
                k += 1
                f += int(self.fps * (2.6 + 1.3 * math.sin(i * 1.7 + k * 2.3) ** 2))
            self.piscadas.append(marcas)
        self.cam_largo = Camera(1.0, L / 2, (lr.PALCO_Y0 + lr.PALCO_Y1) / 2)

    # --- events -----------------------------------------------------------------
    def _montar_eventos(self) -> list[Evento]:
        out: list[Evento] = []
        for s in self.segs:
            if s["tipo"] == "cta":
                continue
            palavras = s.get("palavras", [])
            achados = []
            for v in s.get("visuais", []):
                alvo = _norm(v["palavra"])
                if not alvo or (er.disponivel() and not er.suportado(v["emoji"])):
                    continue
                for w in palavras:
                    nw = _norm(w["texto"])
                    if nw and (nw.startswith(alvo) or alvo.startswith(nw) and len(nw) >= 4):
                        if all(abs(w["inicio"] - a[0]) > 0.3 for a in achados):
                            achados.append((w["inicio"], v["emoji"]))
                        break
            if not achados and s["tipo"] == "item":  # no emoji: one camera beat in the middle of the item
                achados.append(((s["inicio"] + s["fim"]) / 2, ""))
            achados.sort()
            for k, (ini, emo) in enumerate(achados):
                prox = achados[k + 1][0] if k + 1 < len(achados) else s["fim"] + 0.3
                fim = min(max(ini + EVENTO_MIN, min(prox - 0.05, ini + EVENTO_MAX)), s["fim"] + 0.3)
                out.append(Evento(max(0.0, ini - 0.08), fim, emo, s["tipo"], s["item"]))
        return out

    def _evento(self, t: float) -> Evento | None:
        for e in self.eventos:
            if e.inicio <= t < e.fim + SOLTA:
                return e
        return None

    # --- camera -----------------------------------------------------------------
    def _cam_item(self, i: int) -> Camera:
        x0, y0, x1, y1 = self.palco1.posicoes[i].caixa
        return Camera(ZOOM_ITEM, (x0 + x1) / 2, (y0 + y1) / 2 - 25)

    def _cam_rosto(self, i: int) -> Camera:
        pos = self.palco1.posicoes[i]
        return Camera(ZOOM_ROSTO, pos.x, pos.topo_cabeca + 150)

    def _segmento(self, t: float) -> dict:
        atual = self.segs[0]
        for s in self.segs:
            if t >= s["inicio"] - 0.15:
                atual = s
        return atual

    def _base(self, s: dict, t: float) -> Camera:
        if s["tipo"] == "item":
            return self._cam_item(s["item"])
        if s["tipo"] == "abertura":
            gancho = self._cam_rosto(self.n - 1)
            return gancho.misturar(self.cam_largo, _ease(t / GANCHO))
        return Camera(1.0 + 0.01 * max(0.0, t - s["inicio"]), self.cam_largo.cx, self.cam_largo.cy)

    def camera(self, t: float) -> Camera:
        s = self._segmento(t)
        ini = s["inicio"] - 0.15
        cam = self._base(s, t)
        if s["indice"] > 0 and t - ini < TRANSICAO:  # ease from the previous segment's framing
            prev = self.segs[s["indice"] - 1]
            cam = self._base(prev, ini).misturar(cam, _ease((t - ini) / TRANSICAO))
        e = self._evento(t)
        if e is not None:
            k = _ease((t - e.inicio) / ATAQUE) * (1 - _ease((t - e.fim) / SOLTA))
            if e.tipo == "item" and e.item is not None:
                cam = cam.misturar(self._cam_rosto(e.item), k)
            else:
                cam = Camera(cam.z + 0.08 * k, cam.cx, cam.cy)
            idade = t - e.inicio
            if 0 <= idade < 0.25:  # tiny shake on the punch
                amp = 7 * (1 - idade / 0.25)
                cam.cx += amp * math.sin(idade * 90)
                cam.cy += amp * math.cos(idade * 70)
        if s["tipo"] == "item":  # impact shake when an item lands (stronger for the last one)
            idade = t - s["inicio"]
            if 0 <= idade < TREMIDA:
                amp = (30 if s["item"] == self.n - 1 else 16) * (1 - idade / TREMIDA)
                cam.cx += amp * math.sin(idade * 95)
                cam.cy += amp * math.cos(idade * 77)
        return cam

    def _recortar(self, palco_img: Image.Image, cam: Camera) -> Image.Image:
        """Crop the ZOOM_MAX stage render to the camera window, resized to the 1x stage band."""
        z = max(1.0, min(cam.z, ZOOM_MAX))
        ww, wh = min(L * ZOOM_MAX / z, palco_img.width), min(BANDA_H * ZOOM_MAX / z, palco_img.height)
        cx, cy = cam.cx * ZOOM_MAX, (cam.cy - lr.PALCO_Y0) * ZOOM_MAX
        x0 = min(max(cx - ww / 2, 0), palco_img.width - ww)
        y0 = min(max(cy - wh / 2, 0), palco_img.height - wh)
        self._janela = (x0, y0, ww, wh)
        return palco_img.resize((L, BANDA_H), Image.Resampling.BILINEAR, box=(x0, y0, x0 + ww, y0 + wh))

    def _na_tela(self, x: float, y: float) -> tuple[float, float]:
        """Frame px (1x stage layout) -> screen px after the camera crop."""
        x0, y0, ww, wh = self._janela
        return (x * ZOOM_MAX - x0) * L / ww, lr.PALCO_Y0 + ((y - lr.PALCO_Y0) * ZOOM_MAX - y0) * BANDA_H / wh

    # --- figures ------------------------------------------------------------------
    def _estados(self, f: int, t: float, atual: int) -> list[lr.EstadoFigura]:
        e = self.energia[f]
        out = []
        for i in range(self.n):
            est = lr.EstadoFigura(piscando=f in self.piscadas[i])
            if i == atual:
                est.dy = -14 * e
                est.esticar = 1.0 + 0.035 * e
                est.boca = "aberta" if e > 0.45 else "fechada"
                idade = t - self.inicio_item.get(i, -9)
                if 0 <= idade < 0.4:  # entrance hop
                    est.dy -= 28 * math.sin(math.pi * idade / 0.4)
                ev = self._evento(t)
                if ev is not None and ev.item == i and ev.emoji and ev.inicio <= t < ev.inicio + 0.35:
                    est.expressao = "chocado"  # reacts to the emoji
            else:
                est.esticar = 1.0 + 0.006 * math.sin(t * 2.2 + i * 1.3)
                if atual >= 0:  # focus: the narrated item stays solid, the others fade back
                    idade = t - self.inicio_item.get(atual, t)
                    est.opacidade = 1.0 - (1.0 - OPACIDADE_FUNDO) * _ease(idade / 0.35)
            out.append(est)
        return out

    def _revelado(self, i: int, t: float) -> bool:
        return not self.revelar or t >= self.inicio_item.get(i, 0.0) - 0.15

    # --- overlays ---------------------------------------------------------------------
    def _lugar_adesivo(self, e: Evento) -> tuple[float, float]:
        """Fixed screen spot for an emoji: beside the face as framed once the punch-in has landed.

        Following the face frame by frame made the sticker slide ~50 px per frame during the fast
        punch-in (and flip sides when the face crossed the center), which looked like a glitch.
        """
        chave = (e.inicio, e.item)
        if chave not in self._lugares:
            janela = self._janela
            self._recortar(self.palco.fundo, self.camera(e.inicio + ATAQUE + 0.05))
            pos = self.palco1.posicoes[e.item]
            hx, hy = self._na_tela(pos.x, pos.topo_cabeca + 70)
            self._janela = janela
            lado = -1 if pos.x > L / 2 else 1  # fixed by the figure's place on the stairs
            x = min(max(hx + lado * 290, 170), L - 170)
            y = min(max(hy - 10, lr.PALCO_Y0 + 140), lr.PALCO_Y1 - 160)
            self._lugares[chave] = (x, y)
        return self._lugares[chave]

    def _adesivo(self, img: Image.Image, t: float) -> None:
        e = self._evento(t)
        if e is None or not e.emoji or t >= e.fim + 0.15:
            return
        base = er.adesivo(e.emoji, ADESIVO)
        if base is None:
            return
        idade, resta = t - e.inicio, e.fim + 0.15 - t
        k = _ease_back(idade / POP) * min(1.0, resta / 0.15)
        if k <= 0.02:
            return
        ang = 7 * math.sin(idade * 7)
        s = base.resize((max(1, round(base.width * k)), max(1, round(base.height * k))), Image.Resampling.BILINEAR)
        s = s.rotate(ang, resample=Image.Resampling.BICUBIC, expand=True)
        if e.tipo == "item" and e.item is not None:
            x, y0 = self._lugar_adesivo(e)
            y = y0 - 12 * math.sin(idade * 3)
        else:
            x, y = L / 2, lr.PALCO_Y0 + 290 - 12 * math.sin(idade * 3)
        self._faiscas(img, x, y, idade)
        img.paste(s, (round(x - s.width / 2), round(y - s.height / 2)), s)

    def _gancho(self, img: Image.Image, t: float) -> None:
        """Opening: a big pulsing "?" over the hidden last item (curiosity in the first seconds)."""
        abertura = self.segs[0]
        if abertura["tipo"] != "abertura" or t >= abertura["fim"] + 0.2:
            return
        sai = min(1.0, (abertura["fim"] + 0.2 - t) / 0.25)
        k = _ease_back(t / 0.3) * sai * (1 + 0.06 * math.sin(t * 9))
        if k <= 0.02:
            return
        pos = self.palco1.posicoes[self.n - 1]
        x, y = self._na_tela(pos.x, pos.topo_cabeca + 150)
        fnt = fonte_black(max(8, round(230 * k)))
        d = ImageDraw.Draw(img)
        d.text((x, y), "?", font=fnt, fill=lr.AMARELO, stroke_width=max(1, round(12 * k)), stroke_fill=lr.TRACO,
               anchor="mm")

    def _cartao_cta(self, img: Image.Image, t: float) -> None:
        if self.cta is None:
            return
        ini, fim = self.cta
        if not (ini - 0.1 <= t < fim + 0.2):
            return
        sai = min(1.0, (fim + 0.2 - t) / 0.2)
        veu = Image.new("RGBA", (L, BANDA_H), (252, 252, 250, round(185 * min(1.0, (t - ini + 0.1) / 0.2) * sai)))
        img.paste(veu, (0, lr.PALCO_Y0), veu)
        d = ImageDraw.Draw(img)
        fnt = fonte_black(54)
        passo = (fim - ini) / (len(CTA) + 1)
        for j, (emo, txt) in enumerate(CTA):
            idade = t - (ini + j * min(0.45, passo))
            if idade < 0:
                continue
            k = _ease_back(idade / POP) * sai
            pulo = 14 * abs(math.sin((t - ini) * 4 + j))
            x = L * (j + 1) / (len(CTA) + 1)
            y = lr.PALCO_Y0 + BANDA_H * 0.42 - pulo
            base = er.adesivo(emo, 230)
            if base is not None and k > 0.02:
                s = base.resize((max(1, round(base.width * k)), max(1, round(base.height * k))),
                                Image.Resampling.BILINEAR)
                img.paste(s, (round(x - s.width / 2), round(y - s.height / 2)), s)
            if k > 0.5:
                d.text((x, y + 175), txt, font=fnt, fill=lr.AMARELO, stroke_width=8, stroke_fill=lr.TRACO,
                       anchor="mm")

    # --- dopamine layer: slam, flash, sparks, alarm ------------------------------------
    def _texto_slam(self, i: int) -> str:
        rot = self.r.itens[i].rotulo
        m = re.match(r"\s*(\d+\s*[ºª°]?)", rot)
        return (m.group(1).replace(" ", "") if m and re.match(r"\d+[ºª°]", m.group(1).replace(" ", ""))
                else rot).upper()

    def _slam(self, img: Image.Image, t: float, atual: int) -> None:
        """Item number slams onto the screen (big, from 2.3x down to 1x), holds, fades."""
        if atual < 0:
            return
        idade = t - self.inicio_item[atual]
        if not 0 <= idade < SLAM:
            return
        txt = self._texto_slam(atual)
        k = 1.0 + 1.3 * (1 - _ease(idade / 0.14))
        alpha = 1.0 if idade < SLAM - 0.18 else (SLAM - idade) / 0.18
        tam = 300 if len(txt) <= 3 else max(110, round(1500 / max(len(txt), 1)))
        camada = _texto_camada(txt, round(tam * k), self._ultimo(atual))
        if alpha < 1:
            camada = camada.copy()
            camada.putalpha(camada.getchannel("A").point(lambda v: int(v * alpha)))
        img.paste(camada, (round((L - camada.width) / 2), round(SLAM_Y - camada.height / 2)), camada)

    def _ultimo(self, i: int) -> bool:
        return i == self.n - 1

    def _flash(self, img: Image.Image, t: float, atual: int) -> None:
        if atual < 0:
            return
        idade = t - self.inicio_item[atual]
        if 0 <= idade < FLASH:
            a = round(200 * (1 - idade / FLASH))
            cor = (255, 70, 60) if self._ultimo(atual) else (255, 255, 255)
            veu = Image.new("RGBA", (L, A), cor + (a,))
            img.paste(veu, (0, 0), veu)

    def _alarme(self, img: Image.Image, t: float, atual: int) -> None:
        """Red pulsing vignette while the last item (the big reveal) is narrated."""
        if atual != self.n - 1:
            return
        k = 0.55 + 0.45 * abs(math.sin((t - self.inicio_item[atual]) * 4.2))
        v = _vinheta()
        v2 = v.copy()
        v2.putalpha(v.getchannel("A").point(lambda x: int(x * k)))
        img.paste(v2, (0, 0), v2)

    def _faiscas(self, img: Image.Image, x: float, y: float, idade: float) -> None:
        """Burst of short rays around an emoji when it pops."""
        if not 0 <= idade < 0.32:
            return
        d = ImageDraw.Draw(img)
        k = idade / 0.32
        r0, r1 = 150 + 60 * k, 175 + 130 * _ease(k)
        for j in range(12):
            ang = j * math.pi / 6 + 0.26
            pts = [(x + r0 * math.cos(ang), y + r0 * math.sin(ang)), (x + r1 * math.cos(ang), y + r1 * math.sin(ang))]
            w = max(2, round(14 * (1 - k)))
            d.line(pts, fill=lr.TRACO, width=w + 6)
            d.line(pts, fill=lr.AMARELO if j % 2 else (255, 255, 255), width=w)

    # --- first frame, real photos, keyword card --------------------------------------------
    def _quadro_gancho(self, t: float) -> Image.Image:
        """First ~0.9 s: extreme close-up on the (hidden) winner's face under a giant title."""
        img = Image.new("RGB", (L, A), lr.FUNDO)
        rosto = _rosto_close(self.r.itens[self.n - 1].personagem.model_dump_json())
        k = 1.0 + 0.10 * _ease(t / GANCHO_ROSTO)  # slow push-in
        r2 = rosto.resize((round(rosto.width * k), round(rosto.height * k)), Image.Resampling.BILINEAR)
        amp = 14 * max(0.0, 1 - t / 0.25)
        dx, dy = amp * math.sin(t * 90), amp * math.cos(t * 70)
        img.paste(r2, (round((L - r2.width) / 2 + dx), round(1180 - r2.height / 2 + dy)), r2)
        titulo = _titulo_gigante(self.r.titulo)
        kt = 1.0 + 0.07 * (1 - _ease(t / 0.15))  # full size from frame 0 (thumbnail), small slam
        t2 = titulo.resize((max(1, round(titulo.width * kt)), max(1, round(titulo.height * kt))),
                           Image.Resampling.BILINEAR)
        img.paste(t2, (round((L - t2.width) / 2), round(420 - t2.height / 2)), t2)
        if t > GANCHO_ROSTO - 0.08:  # white flash into the normal opening
            veu = Image.new("RGBA", (L, A), (255, 255, 255, round(230 * (t - GANCHO_ROSTO + 0.08) / 0.08)))
            img.paste(veu, (0, 0), veu)
        return img

    def _foto(self, img: Image.Image, t: float, atual: int) -> None:
        """Real photo of the item: pops big right after the number slam, then shrinks to a corner."""
        if atual < 0 or atual not in self.fotos:
            return
        idade = t - self.inicio_item[atual] - FOTO_INICIO
        if idade < 0:
            return
        cartao = _cartao_foto(str(self.fotos[atual]))
        k_enc = _ease((idade - FOTO_GRANDE) / 0.35)  # 0 = big in the middle, 1 = small in the corner
        escala = (0.25 + 0.75 * _ease_back(idade / 0.25)) * (1 - 0.58 * k_enc)
        canto = 1 if self.palco1.posicoes[atual].x < L / 2 else -1  # corner opposite to the emoji side
        x = L / 2 - canto * k_enc * (L / 2 - 175)
        y = lr.PALCO_Y0 + 300 - k_enc * 120
        ang = (-4 if canto > 0 else 4) * (1 - 0.5 * k_enc)
        c = cartao.resize((max(1, round(cartao.width * escala)), max(1, round(cartao.height * escala))),
                          Image.Resampling.BILINEAR).rotate(ang, resample=Image.Resampling.BICUBIC, expand=True)
        img.paste(c, (round(x - c.width / 2), round(y - c.height / 2)), c)

    def _cartao_palavra(self, img: Image.Image, t: float) -> None:
        """Closing: dimmed stage, 'COMENTA A PALAVRA' + the keyword in giant letters (attention challenge)."""
        if not self.r.palavra_chave or t < self.fechamento - 0.1:
            return
        idade = t - self.fechamento + 0.1
        veu = Image.new("RGBA", (L, BANDA_H), (252, 252, 250, round(200 * min(1.0, idade / 0.25))))
        img.paste(veu, (0, lr.PALCO_Y0), veu)
        d = ImageDraw.Draw(img)
        k = _ease_back(idade / 0.3)
        if k > 0.3:
            d.text((L / 2, lr.PALCO_Y0 + 170), "COMENTA A PALAVRA", font=fonte_black(58), fill=lr.TRACO,
                   anchor="mm")
        palavra = self.r.palavra_chave.upper()
        tam = min(200, round(1700 / max(len(palavra), 1)))
        pulso = 1 + 0.05 * math.sin(idade * 8)
        camada = _texto_camada(palavra, max(8, round(tam * max(k, 0.05) * pulso)), False)
        img.paste(camada, (round((L - camada.width) / 2), round(lr.PALCO_Y0 + 380 - camada.height / 2)), camada)
        seta = er.adesivo("\U0001F447", 170)
        if seta is not None and k > 0.5:
            yb = lr.PALCO_Y0 + 610 + 18 * abs(math.sin(idade * 6))
            img.paste(seta, (round(L / 2 - seta.width / 2), round(yb - seta.height / 2)), seta)

    # --- sound map ------------------------------------------------------------------------
    def eventos_sonoros(self) -> list:
        """Sound effects in sync with the visuals (see sfx.py)."""
        from sfx import EventoSom

        out = [EventoSom(0.02, "impacto", -3.0), EventoSom(0.0, "whoosh", -4.0)]
        for i, ini in self.inicio_item.items():
            out.append(EventoSom(max(0.0, ini - 0.28), "whoosh"))
            out.append(EventoSom(ini, "impacto", 3.0 if self._ultimo(i) else 0.0))
        for e in self.eventos:
            if e.emoji:
                out.append(EventoSom(e.inicio, "pop", -2.0))
        if self.cta:
            ini, fim = self.cta
            passo = (fim - ini) / (len(CTA) + 1)
            out += [EventoSom(ini + j * min(0.45, passo), "pop", -1.0) for j in range(len(CTA))]
            out.append(EventoSom(ini + 0.05, "ding", -4.0))
        ultimo = self.inicio_item.get(self.n - 1)
        if ultimo is not None:
            out.append(EventoSom(ultimo, "subida", -2.0))
        out.append(EventoSom(self.fechamento, "whoosh", -3.0))
        if self.r.palavra_chave:
            out += [EventoSom(self.fechamento + 0.05, "impacto", -2.0), EventoSom(self.fechamento + 0.1, "ding", -3.0)]
        for i in self.fotos:
            if i in self.inicio_item:
                out.append(EventoSom(self.inicio_item[i] + FOTO_INICIO, "pop", -3.0))
        out.append(EventoSom(GANCHO_ROSTO - 0.05, "whoosh", -2.0))
        return out

    def _progresso(self, img: Image.Image, t: float) -> None:
        """Segmented progress bar under the title: one segment per item, fills as items are narrated."""
        if t < POP * 1.5:
            return
        larg, alt, gap = 600, 22, 12
        n = self.n
        seg = (larg - gap * (n - 1)) / n
        x0, y = (L - larg) / 2, PROGRESSO_Y
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0 - 12, y - 9, x0 + larg + 12, y + alt + 9], radius=(alt + 18) / 2, fill=lr.FUNDO,
                            outline=lr.TRACO, width=3)
        for i in range(n):
            xa = x0 + i * (seg + gap)
            ini = self.inicio_item.get(i, self.duracao)
            fim = self.fim_item.get(i, self.duracao)
            d.rounded_rectangle([xa, y, xa + seg, y + alt], radius=alt / 2, fill=(225, 227, 232),
                                outline=lr.TRACO, width=3)
            if t >= ini - 0.15:
                k = min(1.0, max(0.0, (t - ini) / max(0.1, fim - ini)))
                w = max(alt, seg * k)
                pulso = 1.0 if t > fim else 0.85 + 0.15 * abs(math.sin(t * 5))
                cor = tuple(int(c * pulso + 255 * (1 - pulso)) for c in lr.AMARELO)
                d.rounded_rectangle([xa, y, xa + w, y + alt], radius=alt / 2, fill=cor, outline=lr.TRACO, width=3)

    def _titulo(self, img: Image.Image, t: float) -> None:
        if t >= POP * 1.5:
            lr.desenhar_titulo(img, self.r.titulo)
            return
        c = lr.camada_titulo(self.r.titulo)
        k = 0.4 + 0.6 * _ease_back(t / (POP * 1.5))
        c2 = c.resize((max(1, round(c.width * k)), max(1, round(c.height * k))), Image.Resampling.BILINEAR)
        img.paste(c2, (round((L - c2.width) / 2), round(lr.TITULO_Y - c2.height / 2)), c2)

    # --- frame ------------------------------------------------------------------------
    def quadro(self, f: int) -> Image.Image:
        t = f / self.fps
        if t < GANCHO_ROSTO:
            return self._quadro_gancho(t)
        atual = self.item_atual[f]
        if atual >= self.n:  # timeline marks cta/closing as n_itens
            atual = -1
        rotulos = [it.rotulo if self._revelado(i, t) else "?" for i, it in enumerate(self.r.itens)]
        palco_img = self.palco.desenhar(atual if atual >= 0 else None, self._estados(f, t, atual), rotulos=rotulos)
        img = Image.new("RGB", (L, A), lr.FUNDO)
        img.paste(self._recortar(palco_img, self.camera(t)), (0, lr.PALCO_Y0))
        self._alarme(img, t, atual)
        self._gancho(img, t)
        self._foto(img, t, atual)
        self._adesivo(img, t)
        self._cartao_cta(img, t)
        self._cartao_palavra(img, t)
        self._slam(img, t, atual)
        self._titulo(img, t)
        self._progresso(img, t)
        self._flash(img, t, atual)
        if atual >= 0:
            idade = t - self.inicio_item[atual]
            lr.desenhar_rotulo(img, self.r.itens[atual].rotulo, escala=0.55 + 0.45 * _ease_back(idade / POP),
                               alpha=min(1.0, max(idade, 0) / 0.08 + 0.2))
        self.legendas.desenhar(img, t, lr.LEGENDA_Y)
        return img

    def quadros_chave(self) -> list[tuple[int, str]]:
        """Frames worth reviewing: hook, emoji pops, CTA, every item, closing."""
        out = [(0, "1º quadro"), (int(self.fps * 0.5), "0,5 s close"), (int(self.fps * 1.1), "1,1 s abertura")]
        for i, ini in self.inicio_item.items():
            if i in self.fotos:
                out.append((int((ini + FOTO_INICIO + 0.6) * self.fps), f"item {i + 1} foto"))
        for e in self.eventos:
            if e.emoji:
                out.append((int((e.inicio + 0.45) * self.fps), f"{e.tipo} {e.emoji}"))
        for i, ini in self.inicio_item.items():
            out.append((int(ini * self.fps) + 6, f"item {i + 1} entrada"))
        if self.cta:
            out.append((int((self.cta[0] + 1.3) * self.fps), "cta"))
        out.append((int((self.fechamento + 1.0) * self.fps), "fechamento"))
        out = sorted({min(f, self.n_frames - 1): r for f, r in out}.items())
        return out


@lru_cache(maxsize=64)
def _texto_camada(txt: str, tam: int, vermelho: bool) -> Image.Image:
    fnt = fonte_black(max(8, tam))
    caixa = fnt.getbbox(txt, stroke_width=max(2, tam // 14))
    w, h = caixa[2] - caixa[0] + 40, caixa[3] - caixa[1] + 40
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    sombra = max(4, tam // 22)
    d.text((w / 2 + sombra, h / 2 + sombra), txt, font=fnt, fill=lr.TRACO, anchor="mm",
           stroke_width=max(2, tam // 14), stroke_fill=lr.TRACO)
    d.text((w / 2, h / 2), txt, font=fnt, fill=(255, 70, 60) if vermelho else lr.AMARELO, anchor="mm",
           stroke_width=max(2, tam // 14), stroke_fill=lr.TRACO)
    return img


@lru_cache(maxsize=4)
def _rosto_close(personagem_json: str) -> Image.Image:
    """Huge render of a character's face (shocked), cropped square, 1150 px wide."""
    import figure_renderer as fr
    from schemas import Personagem

    p = Personagem.model_validate_json(personagem_json)
    alt = 2600
    fig = fr.renderizar(p, alt, "chocado")
    g = fr._Geo(p)
    k = alt / fr.ALT_U
    cx, cy = fr.CX * k, (g.olho_y + g.d * 0.08) * k
    lado = g.d * 1.3 * k
    caixa = (round(cx - lado / 2), round(cy - lado / 2), round(cx + lado / 2), round(cy + lado / 2))
    return fig.crop(caixa).resize((1150, 1150), Image.Resampling.LANCZOS)


@lru_cache(maxsize=4)
def _titulo_gigante(titulo: str) -> Image.Image:
    """Title in huge heavy letters, up to 3 lines, white with a thick dark outline; numbers in yellow."""
    palavras = titulo.upper().split()
    for tam in range(170, 70, -8):
        fnt = fonte_black(tam)
        linhas, atual = [], ""
        for w in palavras:
            teste = f"{atual} {w}".strip()
            if fnt.getlength(teste) > L - 160 and atual:
                linhas.append(atual)
                atual = w
            else:
                atual = teste
        linhas.append(atual)
        if len(linhas) <= 3 and max(fnt.getlength(x) for x in linhas) <= L - 160:
            break
    lh = round(tam * 1.02)
    img = Image.new("RGBA", (L, lh * len(linhas) + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(linhas):
        y = 30 + lh * (i + 0.5)
        x = L / 2 - fnt.getlength(ln) / 2
        for w in ln.split():  # word by word so numbers can be yellow
            cor = lr.AMARELO if any(ch.isdigit() for ch in w) else (255, 255, 255)
            sw = max(4, tam // 12)
            d.text((x + 8, y + 8), w, font=fnt, fill=lr.TRACO, anchor="lm", stroke_width=sw, stroke_fill=lr.TRACO)
            d.text((x, y), w, font=fnt, fill=cor, anchor="lm", stroke_width=sw, stroke_fill=lr.TRACO)
            x += fnt.getlength(w + " ")
    return img


@lru_cache(maxsize=16)
def _cartao_foto(caminho: str) -> Image.Image:
    """Photo cropped 4:3 in a white frame with a dark outline and shadow (instant-photo look)."""
    from PIL import ImageFilter, ImageOps

    foto = ImageOps.fit(Image.open(caminho).convert("RGB"), (620, 465), Image.Resampling.LANCZOS)
    borda, sombra = 16, 14
    w, h = foto.width + 2 * borda, foto.height + 2 * borda
    img = Image.new("RGBA", (w + sombra + 20, h + sombra + 20), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([10 + sombra, 10 + sombra, 10 + w + sombra, 10 + h + sombra], radius=14,
                                         fill=(20, 20, 30, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10, 10, 10 + w, 10 + h], radius=14, fill=(255, 255, 255, 255), outline=lr.TRACO, width=6)
    img.paste(foto, (10 + borda, 10 + borda))
    d.rectangle([10 + borda, 10 + borda, 10 + borda + foto.width, 10 + borda + foto.height], outline=lr.TRACO,
                width=3)
    return img


@lru_cache(maxsize=1)
def _vinheta() -> Image.Image:
    """Red vignette: transparent center, red edges."""
    import numpy as np

    y, x = np.mgrid[0:A, 0:L].astype(np.float32)
    d = np.sqrt(((x - L / 2) / (L / 2)) ** 2 + ((y - A / 2) / (A / 2)) ** 2)
    alpha = (np.clip((d - 0.62) / 0.55, 0, 1) ** 1.6 * 170).astype(np.uint8)
    img = Image.new("RGBA", (L, A), (235, 40, 40, 0))
    img.putalpha(Image.fromarray(alpha, "L"))
    return img


def carregar_timeline(caminho: Path) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))
