"""Measure the narrator's words per second over the fallback rankings.

Usage: python tools/medir_vozes.py [--tts edge|mock]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
import voice_engine as ve  # noqa: E402
from schemas import Ranking, listar_fallbacks  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tts", choices=list(ve.MOTORES), default="edge")
    args = ap.parse_args(argv)
    rankings = [Ranking.carregar(config.RANKINGS / f"{n}.json") for n in listar_fallbacks()]
    pps = ve.medir_palavras_por_segundo(rankings, ve.criar_motor(args.tts))
    print(f"narrador ({config.NARRADOR['voz']} {config.NARRADOR['rate']}): {pps} palavras/s "
          f"(config atual {config.NARRADOR['palavras_por_segundo']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
