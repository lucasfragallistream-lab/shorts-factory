"""Miniseries audio: one Brazilian edge-tts voice per role, line timing, SFX, rain ambience, BGM, final mix.

Voices (pt-BR only, neutral accent): narrator Thalita; older women Francisca low/slow; younger women Francisca
high/fast; men Antonio, faster for villains and deep/slow for the mystery role. Emotion nudges rate and pitch.
Lines play back to back (small gaps, a longer one between scenes); if the speech runs past the end card it is
sped up (max ATEMPO_MAX), otherwise the end card simply lasts longer. Output is exactly `duracao` seconds.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import sfx
import voice_engine as ve
from novela_schema import Episodio

INICIO = 0.15
GAP_FALA = 0.22
GAP_CENA = 0.45
CARTAO_FIM_MIN = 3.2  # s reserved at the end for the "CONTINUA" card
ATEMPO_MAX = 1.12
CHUVA_DB = -30.0

THALITA = "pt-BR-ThalitaMultilingualNeural"
FRANCISCA = "pt-BR-FranciscaNeural"
ANTONIO = "pt-BR-AntonioNeural"

_EMOCAO = {"raiva": (6, 2), "deboche": (4, 3), "choque": (4, 0), "chorando": (-6, -3), "triste": (-5, -2),
           "medo": (2, 2), "esperanca": (0, 2), "neutra": (0, 0)}


def _fmt(rate: int, pitch: int) -> tuple[str, str]:
    return f"{rate:+d}%", f"{pitch:+d}Hz"


def voz(ep: Episodio, quem: str, emocao: str) -> dict:
    if quem == "narrador":
        nome, rate, pitch = THALITA, 2, 0
    else:
        m = ep.membro(quem)
        p = m.personagem
        if p.sexo == "feminino":
            if p.idade in ("meia_idade", "idoso"):
                nome, rate, pitch = FRANCISCA, -10, -7
            else:
                nome, rate, pitch = FRANCISCA, 6, 12
        else:
            if m.papel in ("misterio", "aliado") and p.idade not in ("crianca", "adolescente"):
                nome, rate, pitch = ANTONIO, -8, -14
            elif p.idade in ("idoso", "meia_idade"):
                nome, rate, pitch = ANTONIO, -6, -9
            else:
                nome, rate, pitch = ANTONIO, 8, 5
    dr, dp = _EMOCAO.get(emocao, (0, 0))
    r, pt = _fmt(rate + dr, pitch + dp)
    return {"voz": nome, "rate": r, "pitch": pt}


@dataclass
class ResultadoNovela:
    wav: Path
    timeline: Path
    atempo: float


def gerar(ep: Episodio, duracao: float, pasta: Path, motor=None, bgm: Path | None = None) -> ResultadoNovela:
    import video_assembler as va

    motor = motor or ve.MotorEdge()
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = [(ci, fi, f) for ci, c in enumerate(ep.cenas) for fi, f in enumerate(c.falas)]
    audios = motor.sintetizar_lote([(f.texto, voz(ep, f.quem, f.emocao)) for _, _, f in linhas])
    gaps = [0.0] + [GAP_CENA if linhas[i][0] != linhas[i - 1][0] else GAP_FALA for i in range(1, len(linhas))]
    fala = sum(a.duracao for a in audios)
    disponivel = duracao - CARTAO_FIM_MIN - INICIO - sum(gaps)
    fator = 1.0
    if fala > disponivel:
        fator = fala / disponivel
        if fator > ATEMPO_MAX:
            raise ve.ErroDuracao(f"as falas somam {fala:.1f} s e não cabem em {duracao} s (precisaria acelerar "
                                 f"{fator:.2f}x); encurte o roteiro")
        audios = [ve.aplicar_atempo(a, fator) for a in audios]
    total = int(round(duracao * ve.SR))
    mix = np.zeros(total, np.float32)
    t = INICIO
    falas_tl, cenas_tl = [], [{"inicio": None, "fim": None} for _ in ep.cenas]
    for (ci, fi, f), a, g in zip(linhas, audios, gaps):
        t += g
        ini = int(round(t * ve.SR))
        mix[ini:ini + len(a.amostras)] += a.amostras[: max(0, total - ini)]
        fim = t + a.duracao
        falas_tl.append({"cena": ci, "fala": fi, "quem": f.quem, "texto": f.texto, "emocao": f.emocao,
                         "enquadramento": f.enquadramento, "destaque": f.destaque, "gesto": f.gesto,
                         "acao": f.acao, "alvo": f.alvo, "inicio": round(t, 4),
                         "fim": round(fim, 4),
                         "palavras": [{"texto": w.texto, "inicio": round(t + w.inicio, 4), "fim": round(t + w.fim, 4)}
                                      for w in a.palavras]})
        if cenas_tl[ci]["inicio"] is None:
            cenas_tl[ci]["inicio"] = round(max(0.0, t - g / 2) if ci else 0.0, 4)
        t = fim
    for ci in range(len(cenas_tl)):  # each scene lasts until the next starts; the last one until the end card
        cenas_tl[ci]["fim"] = cenas_tl[ci + 1]["inicio"] if ci + 1 < len(cenas_tl) else round(t + 0.35, 4)
    fim_fala = round(t, 4)

    # sound design
    eventos = [sfx.EventoSom(0.0, "impacto", 2.0)]
    for c in cenas_tl[1:]:
        eventos.append(sfx.EventoSom(c["inicio"], "whoosh", -2.0))
    for fl in falas_tl:
        if fl["destaque"]:
            eventos.append(sfx.EventoSom(fl["inicio"], "impacto", -3.0))
        if fl["acao"] == "empurra":
            eventos.append(sfx.EventoSom(fl["inicio"] + 0.35, "impacto", 1.0))
        elif fl["acao"] in ("entra", "sai"):
            eventos.append(sfx.EventoSom(fl["inicio"] if fl["acao"] == "entra" else fl["fim"], "whoosh", -6.0))
        if re.search(r"\bporta\b", fl["texto"], re.I) and fl["quem"] == "narrador":
            eventos.append(sfx.EventoSom(fl["inicio"] + 0.4, "impacto", 3.0))  # door slam
    cartao = cenas_tl[-1]["fim"]
    eventos += [sfx.EventoSom(cartao, "subida", -1.0), sfx.EventoSom(cartao, "impacto", 4.0)]
    efeitos = sfx.trilha_sfx(eventos, duracao)
    for ci, c in enumerate(ep.cenas):  # rain ambience: soft filtered noise during rainy scenes
        if c.chuva:
            a, b = int(cenas_tl[ci]["inicio"] * ve.SR), int(cenas_tl[ci]["fim"] * ve.SR)
            rng = np.random.default_rng(11)
            ruido = sfx._passa_baixa(rng.normal(size=b - a), 0.18).astype(np.float32)
            ruido *= 10 ** (CHUVA_DB / 20) / (np.max(np.abs(ruido)) or 1)
            env = np.minimum(1, np.minimum(np.arange(b - a), np.arange(b - a)[::-1]) / (0.4 * ve.SR))
            efeitos[a:b] += ruido * env.astype(np.float32)
    voz_wav = ve.salvar_wav(pasta / "voz.wav", mix)
    voz_sfx = ve.salvar_wav(pasta / "voz_sfx.wav", mix + efeitos[: len(mix)])
    final = va.mixar_audio(voz_sfx, pasta / "audio.wav", duracao, bgm)
    tl = {"duracao": duracao, "fps": 30, "atempo": round(fator, 4), "fim_fala": fim_fala, "cartao": cartao,
          "cenas": cenas_tl, "falas": falas_tl, "audio": str(final), "voz": str(voz_wav)}
    destino = pasta / "timeline.json"
    destino.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    return ResultadoNovela(final, destino, fator)
