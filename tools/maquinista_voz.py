"""Voice + word timeline for one "Você é o Maquinista" episode (Edge pt-BR voices, fast kit pacing).

Usage: python tools/maquinista_voz.py maquinista/ep2.json motion/trolley/src/ep2
Writes <dest>/voz.wav and <dest>/timeline.json: lines and words with real start/end seconds. The speech is fitted
to end at FALA_FIM (the 10 s countdown starts at CONTAGEM) with small gaps between lines (kit: longest pause ~0.4 s).

Line options in the script: "respira": true leaves room for a breath before the line (the sound tool places a real
inhale there: an out-of-breath narrator), "pausa_antes": s sets the gap before it (a beat before a punchline).
Script option "atempo": fixed speed-up (an episode that reuses another one's takes repeats its lines at its speed).
The narrator is processed to sound urgent over the train noise (presence boost, hard compression, soft clip).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import voice_engine as ve  # noqa: E402
from ffmpeg_utils import find_ffmpeg  # noqa: E402

GAP = 0.12  # between lines
GAP_PERSONAGEM = 0.28  # around a character's line
RESPIRO = 0.34  # extra room for a breath
CONTAGEM = 51.0
FALA_FIM = 50.6
VOZES = {  # fast, tense narrator (kit: 3.3-3.8 words/s); characters with their own colour
    "narrador": {"voz": "pt-BR-ThalitaMultilingualNeural", "rate": "+32%", "pitch": "+4Hz"},
    "cida": {"voz": "pt-BR-FranciscaNeural", "rate": "-4%", "pitch": "-12Hz"},
    "helena": {"voz": "pt-BR-FranciscaNeural", "rate": "-12%", "pitch": "+6Hz"},
    "pai": {"voz": "pt-BR-AntonioNeural", "rate": "-10%", "pitch": "-9Hz"},
    "doutora": {"voz": "pt-BR-FranciscaNeural", "rate": "+8%", "pitch": "+3Hz"},
    "vovo": {"voz": "pt-BR-AntonioNeural", "rate": "+12%", "pitch": "-3Hz"},
}
# urgent narrator: cut the boom, push the presence, squash the dynamics, round the peaks (shouting over a train)
URGENTE = ("highpass=f=130,equalizer=f=280:t=q:w=1:g=-3,equalizer=f=3100:t=q:w=0.9:g=5,"
           "equalizer=f=7500:t=q:w=1:g=2,acompressor=threshold=0.09:ratio=6:attack=2:release=45:makeup=3,"
           "asoftclip=type=atan:threshold=0.8")


def processar(amostras: np.ndarray, filtro: str) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.wav", Path(d) / "b.wav"
        ve.salvar_wav(a, amostras)
        subprocess.run([find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(a), "-af", filtro,
                        "-ar", str(ve.SR), "-ac", "1", str(b)], check=True)
        y = ve.ler_wav(b).astype(np.float32)
    y = y[: len(amostras)]
    y = np.pad(y, (0, len(amostras) - len(y)))
    return (y * (np.max(np.abs(amostras)) / (np.max(np.abs(y)) or 1))).astype(np.float32)  # same peak as before


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    roteiro = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    destino = Path(argv[1])
    destino.mkdir(parents=True, exist_ok=True)
    falas = roteiro["falas"]
    inicio = float(roteiro.get("inicio", 0.12))
    audios = ve.MotorEdge().sintetizar_lote([(f["texto"], VOZES[f["quem"]]) for f in falas])
    gaps = []
    for i, f in enumerate(falas):
        if i == 0:
            g = inicio
        elif "pausa_antes" in f:
            g = float(f["pausa_antes"])
        else:
            g = GAP_PERSONAGEM if (f["quem"] != "narrador" or falas[i - 1]["quem"] != "narrador") else GAP
        gaps.append(g + (RESPIRO if f.get("respira") and i else 0.0))
    fala = sum(a.duracao for a in audios)
    fator = fala / max(1e-3, FALA_FIM - sum(gaps))
    if "atempo" in roteiro:  # same speed-up as the episode whose takes (and lines) are reused, so they stay in sync
        if fator > float(roteiro["atempo"]) + 1e-3:
            raise SystemExit(f"com atempo fixo {roteiro['atempo']} a fala não cabe até {FALA_FIM} s "
                             f"(precisaria {fator:.3f}x); encurte")
        fator = float(roteiro["atempo"])
    if fator > 1.0:
        if fator > 1.15:
            raise SystemExit(f"fala de {fala:.1f} s não cabe até {FALA_FIM} s (precisaria {fator:.2f}x); encurte")
        audios = [ve.aplicar_atempo(a, fator) for a in audios]
    total = int(round(61.0 * ve.SR))
    narr, chars = np.zeros(total, np.float32), np.zeros(total, np.float32)
    t, linhas, palavras, respiros = 0.0, [], [], []
    for f, a, g in zip(falas, audios, gaps):
        if f.get("respira") and linhas:
            respiros.append(round(t + 0.04, 3))
        t += g
        i = int(round(t * ve.SR))
        alvo = narr if f["quem"] == "narrador" else chars
        alvo[i:i + len(a.amostras)] += a.amostras[: total - i]
        ws = [{"w": w.texto, "a": round(t + w.inicio, 3), "b": round(t + w.fim, 3), "linha": f["id"], "quem": f["quem"]}
              for w in a.palavras]
        linhas.append({"id": f["id"], "quem": f["quem"], "texto": f["texto"], "a": round(t, 3), "b": round(t + a.duracao, 3),
                       "w0": len(palavras), "w1": len(palavras) + len(ws)})
        palavras += ws
        t += a.duracao
    if roteiro.get("urgente", True):
        narr = processar(narr, URGENTE)
    ve.salvar_wav(destino / "voz.wav", np.clip(narr + chars, -1, 1))
    n = len(palavras)
    # speaking rate without the planned beats (breaths, pause before a punchline): what the kit measures
    planejado = sum(RESPIRO for f in falas[1:] if f.get("respira")) + sum(float(f.get("pausa_antes", 0)) for f in falas)
    tl = {"fps": 30, "duracao": 61.0, "contagem": CONTAGEM, "fala_fim": round(t, 3), "atempo": round(max(1.0, fator), 4),
          "palavras_por_s": round(n / (t - inicio - planejado), 2), "linhas": linhas, "palavras": palavras, "respiros": respiros,
          **{k: roteiro[k] for k in ("serie", "numero", "titulo", "trilho_a", "trilho_b", "pergunta")}}
    (destino / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{n} palavras, fala termina em {t:.2f} s, {tl['palavras_por_s']} palavras/s, atempo {tl['atempo']}, "
          f"{len(respiros)} respiros")
    return 0


if __name__ == "__main__":
    sys.exit(main())
