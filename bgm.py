"""Background music.

If the user supplies assets/bgm.mp3 it is used for every episode. Otherwise a
royalty-free track is synthesized locally per style (numpy only, deterministic
per seed) and cached in cache/bgm/:
- leve (default): bouncy major-key ukulele/marimba groove, 112 bpm.
- tenso: dark minor drone, heartbeat pulse and sparse bells, 72 bpm.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

import config

SR = 48000
VERSAO = 1  # bump when the synthesis changes, to invalidate the cache
DURACAO_PADRAO = 64.0


# --- building blocks -------------------------------------------------------
def _env(n: int, ataque: float, decaimento: float) -> np.ndarray:
    """Linear attack then exponential decay (time constant `decaimento` s)."""
    t = np.arange(n) / SR
    a = max(int(ataque * SR), 1)
    env = np.exp(-np.maximum(t - ataque, 0) / max(decaimento, 1e-3))
    env[:a] *= np.linspace(0, 1, a)
    return env


def _tom(n: int, freq: float, harmonicos=(1.0,), detune: float = 0.0, fase: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, amp in enumerate(harmonicos, start=1):
        if amp:
            out += amp * np.sin(2 * np.pi * freq * k * (1 + detune) * t + fase * k)
    return out


def _somar(buf: np.ndarray, t0: float, sinal: np.ndarray, amp: float = 1.0) -> None:
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sinal))
    buf[i:j] += amp * sinal[: j - i]


def _passa_baixa(x: np.ndarray, corte: float) -> np.ndarray:
    esp = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    esp *= 1.0 / (1.0 + (f / corte) ** 4)
    return np.fft.irfft(esp, len(x))


def _passa_alta(x: np.ndarray, corte: float) -> np.ndarray:
    return x - _passa_baixa(x, corte)


def _eco(x: np.ndarray, atrasos=((0.23, 0.35), (0.41, 0.22), (0.67, 0.12))) -> np.ndarray:
    out = x.copy()
    for seg, g in atrasos:
        d = int(seg * SR)
        out[d:] += g * x[:-d]
    return out


def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _normalizar(x: np.ndarray, rms_alvo: float = 0.16, pico_max: float = 0.95) -> np.ndarray:
    rms = float(np.sqrt(np.mean(x ** 2))) or 1.0
    x = x * (rms_alvo / rms)
    pico = float(np.max(np.abs(x))) or 1.0
    return x * min(1.0, pico_max / pico)


def _fades(x: np.ndarray, ini: float = 0.5, fim: float = 2.0) -> np.ndarray:
    a, b = int(ini * SR), int(fim * SR)
    x[:a] *= np.linspace(0, 1, a)
    x[-b:] *= np.linspace(1, 0, b)
    return x


# --- tracks ----------------------------------------------------------------
def _leve(dur: float, rng: np.random.Generator) -> np.ndarray:
    n = int(dur * SR)
    buf = np.zeros(n)
    beat = 60 / 112
    compasso = 4 * beat
    # I - vi - IV - V in C (MIDI roots for the bass, triads for the chords)
    acordes = [(48, (60, 64, 67)), (45, (57, 60, 64)), (41, (53, 57, 60)), (43, (55, 59, 62))]
    escala = [72, 74, 76, 79, 81, 84]  # C major pentatonic, octave 5

    def frase():
        return [[None if rng.random() < 0.35 else int(rng.choice(escala)) for _ in range(8)] for _ in range(4)]

    frases = {"A": frase(), "B": frase()}
    forma = "AABA" * 8
    n_comp = int(dur / compasso) + 1
    for c in range(n_comp):
        t0 = c * compasso
        raiz, triade = acordes[c % 4]
        melodia = frases[forma[(c // 4) % len(forma)]][c % 4]
        for b in range(4):
            tb = t0 + b * beat
            nota = raiz if b % 2 == 0 else raiz + 7
            m = int(0.22 * SR)
            _somar(buf, tb, _tom(m, _hz(nota), (1, 0.5, 0.2)) * _env(m, 0.004, 0.09), 0.55)
            if b % 2 == 0:  # soft kick
                k = int(0.16 * SR)
                tt = np.arange(k) / SR
                _somar(buf, tb, np.sin(2 * np.pi * (50 + 70 * np.exp(-tt * 30)) * tt) * _env(k, 0.002, 0.05), 0.5)
            ts = tb + beat / 2  # offbeat ukulele stab
            m = int(0.14 * SR)
            for i, nt in enumerate(triade):
                _somar(buf, ts + i * 0.008, _tom(m, _hz(nt), (1, 0, 0.33, 0, 0.2)) * _env(m, 0.003, 0.05), 0.12)
            h = int(0.03 * SR)  # hi-hat
            _somar(buf, ts, rng.normal(0, 1, h) * _env(h, 0.001, 0.008), 0.08)
        for i, nt in enumerate(melodia):
            if nt is not None:
                m = int(0.3 * SR)
                _somar(buf, t0 + i * beat / 2, _tom(m, _hz(nt), (1, 0, 0, 0.25)) * _env(m, 0.002, 0.08), 0.22)
    return _fades(_normalizar(_passa_alta(buf, 40.0)))  # remove DC/rumble


def _tenso(dur: float, rng: np.random.Generator) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    beat = 60 / 72
    secao = 16 * beat  # 4 bars per chord
    # drone on A with slow breathing
    drone = sum(_tom(n, f, (1, 0.5, 0.33, 0.25, 0.2), detune=d) for f in (55.0, 82.41, 110.0) for d in (-0.003, 0.003))
    drone = _passa_baixa(drone, 260.0) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * t - np.pi / 2))
    buf = 0.5 * drone / (np.max(np.abs(drone)) or 1)
    # pad chords: Am - F - Dm - E
    acordes = [(57, 60, 64), (53, 57, 60), (50, 53, 57), (52, 56, 59)]
    m = int((secao + 1.5) * SR)
    env_pad = np.minimum(1.0, np.minimum(np.arange(m) / (1.2 * SR), (m - np.arange(m)) / (1.5 * SR)))
    for s in range(int(dur / secao) + 1):
        pad = sum(_tom(m, _hz(nt), (1, 0, 0.2), detune=0.002) for nt in acordes[s % 4])
        _somar(buf, s * secao, _passa_baixa(pad, 900.0) * env_pad, 0.10)
    # heartbeat every 2 beats (lub-dub)
    k = int(0.2 * SR)
    tt = np.arange(k) / SR
    batida = np.sin(2 * np.pi * (45 + 25 * np.exp(-tt * 25)) * tt) * _env(k, 0.003, 0.06)
    tb = 0.0
    while tb < dur:
        _somar(buf, tb, batida, 0.55)
        _somar(buf, tb + 0.26, batida, 0.35)
        tb += 2 * beat
    # sparse bells with echoes
    sinos = np.zeros(n)
    notas = [69, 72, 76, 79, 71, 74]
    tb = 2 * beat
    while tb < dur - 3:
        m = int(3.0 * SR)
        f = _hz(int(rng.choice(notas)))
        sino = sum(a * np.sin(2 * np.pi * f * r * np.arange(m) / SR) for r, a in ((1, 1), (2.76, 0.4), (5.4, 0.15)))
        _somar(sinos, tb, sino * _env(m, 0.005, 0.9), 0.10)
        tb += beat * float(rng.choice([4, 6, 8]))
    buf += _eco(sinos)
    # noise swell every 8 bars
    ruido = _passa_baixa(_passa_alta(rng.normal(0, 1, n), 300.0), 1800.0)
    ciclo = (t % (2 * secao)) / (2 * secao)
    buf += 0.05 * ruido / (np.max(np.abs(ruido)) or 1) * ciclo ** 3
    return _fades(_normalizar(buf), 1.0, 2.5)


_FAIXAS = {"leve": _leve, "tenso": _tenso}


def gerar(estilo: str, destino: Path, duracao: float = DURACAO_PADRAO, seed: int = 0) -> Path:
    if estilo not in _FAIXAS:
        raise ValueError(f"estilo de trilha desconhecido: {estilo} (disponíveis: {', '.join(_FAIXAS)})")
    audio = _FAIXAS[estilo](duracao, np.random.default_rng(seed))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return destino


def obter_bgm(estilo: str = config.ESTILO_BGM, seed: int = 0) -> Path:
    """assets/bgm.mp3 when present; else the generated track for the style (cached)."""
    if config.BGM.exists():
        return config.BGM
    caminho = config.CACHE / "bgm" / f"bgm_{estilo}_s{seed}_v{VERSAO}.wav"
    if not caminho.exists():
        gerar(estilo, caminho, seed=seed)
    return caminho
