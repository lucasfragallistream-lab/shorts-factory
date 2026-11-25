"""Procedural sound effects (no samples, no downloads, no licenses): whoosh, pop, impact, riser, ding.

`trilha_sfx(eventos, duracao)` lays them on a 48 kHz mono track that is summed with the narration
before the final mix, so the BGM ducking and the -14 LUFS normalization treat them like the voice.
Every sound is deterministic (seeded) and peaks around NIVEL dBFS before the mix.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

SR = 48000
NIVEL_DB = -14.0  # peak of each effect relative to full scale (voice peaks ~-1 dBFS before normalization)
TIPOS = ("whoosh", "pop", "impacto", "subida", "ding")


@dataclass(frozen=True)
class EventoSom:
    t: float  # seconds; for "subida" it is the END (the riser builds up to this moment)
    tipo: str
    ganho_db: float = 0.0


def _t(seg: float) -> np.ndarray:
    return np.arange(int(seg * SR)) / SR


def _passa_baixa(x: np.ndarray, alfa: np.ndarray | float) -> np.ndarray:
    """One-pole low-pass; `alfa` may change per sample (0 < alfa <= 1, higher = brighter)."""
    alfa = np.broadcast_to(np.asarray(alfa, dtype=np.float64), x.shape)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alfa[i] * (x[i] - acc)
        y[i] = acc
    return y


def _normalizar(x: np.ndarray, db: float = NIVEL_DB) -> np.ndarray:
    pico = float(np.max(np.abs(x))) or 1.0
    return (x / pico * 10 ** (db / 20)).astype(np.float32)


@lru_cache(maxsize=None)
def som(tipo: str) -> np.ndarray:
    rng = np.random.default_rng(TIPOS.index(tipo) + 7)
    if tipo == "whoosh":  # filtered noise sweeping up then down
        t = _t(0.42)
        env = np.sin(np.pi * t / t[-1]) ** 2
        varre = 0.02 + 0.25 * np.sin(np.pi * t / t[-1])
        x = _passa_baixa(rng.normal(size=len(t)), varre) * env
    elif tipo == "pop":  # fast pitch drop with a click
        t = _t(0.12)
        f = 1100 * np.exp(-t * 28) + 260
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32)
        x[: int(0.004 * SR)] += rng.normal(size=int(0.004 * SR)) * 0.5
    elif tipo == "impacto":  # sub boom + noise crack
        t = _t(0.9)
        f = 48 + 90 * np.exp(-t * 18)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
        crack = _passa_baixa(rng.normal(size=len(t)), 0.35) * np.exp(-t * 30)
        x = boom + 0.6 * crack
    elif tipo == "subida":  # tension riser: rising tone + brightening noise, cut at the end
        t = _t(1.6)
        k = t / t[-1]
        f = 180 + 900 * k ** 2
        tom = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
        ruido = _passa_baixa(rng.normal(size=len(t)), 0.02 + 0.4 * k)
        x = (0.6 * tom + ruido) * k ** 1.6
    elif tipo == "ding":  # bright bell
        t = _t(0.7)
        x = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1320, 1.0), (1980, 0.5), (2640, 0.25))) * np.exp(-t * 6)
    else:
        raise ValueError(f"efeito desconhecido: {tipo}")
    return _normalizar(np.asarray(x, dtype=np.float64))


def trilha_sfx(eventos: list[EventoSom], duracao: float) -> np.ndarray:
    out = np.zeros(int(round(duracao * SR)), np.float32)
    for e in eventos:
        s = som(e.tipo) * 10 ** (e.ganho_db / 20)
        ini = int(round((e.t - (len(s) / SR if e.tipo == "subida" else 0.0)) * SR))
        a, b = max(ini, 0), min(ini + len(s), len(out))
        if b > a:
            out[a:b] += s[a - ini:b - ini]
    return out
