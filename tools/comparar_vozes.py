"""Phase R3: same narration with edge-tts and several Chatterbox settings, for choosing by ear.

Usage: python tools/comparar_vozes.py [--ranking crises]
Writes output/vozes/NN_nome.wav (opening + first item) and prints duration, words/s and generation time.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
import voice_engine as ve  # noqa: E402
from schemas import Ranking, contar_palavras  # noqa: E402

VARIANTES = [
    ("chatterbox_padrao", {"exaggeration": 0.5, "cfg_weight": 0.5, "temperature": 0.8}),
    ("chatterbox_calmo", {"exaggeration": 0.4, "cfg_weight": 0.3, "temperature": 0.7}),
    ("chatterbox_animado", {"exaggeration": 0.7, "cfg_weight": 0.3, "temperature": 0.8}),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ranking", default="crises")
    args = ap.parse_args(argv)
    r = Ranking.carregar(config.RANKINGS / f"{args.ranking}.json")
    textos = [r.abertura, r.itens[0].narracao]
    palavras = sum(contar_palavras(t) for t in textos)
    pasta = config.OUTPUT / "vozes"
    pasta.mkdir(parents=True, exist_ok=True)
    motores = [("edge_antonio", ve.MotorEdge(), None)] + [(n, ve.MotorChatterbox(), c) for n, c in VARIANTES]
    pausa = np.zeros(int(0.4 * ve.SR), np.float32)
    for k, (nome, motor, cfg) in enumerate(motores, 1):
        if cfg:
            motor.cfg = dict(cfg)
        t0 = time.perf_counter()
        audios = motor.sintetizar_lote([(t, ve.voz_narrador()) for t in textos])
        dt = time.perf_counter() - t0
        fala = sum(a.duracao for a in audios)
        destino = pasta / f"{k:02d}_{nome}.wav"
        ve.salvar_wav(destino, np.concatenate([audios[0].amostras, pausa, audios[1].amostras]))
        print(f"{destino.name}: fala {fala:.1f} s | {palavras / fala:.2f} palavras/s | gerado em {dt:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
