"""Builds one miniseries episode end to end: Edge voices -> timeline -> HyperFrames project -> check (-> render).

Usage: python tools/novela_episodio.py output/minisserie/preco_da_ingratidao_ep2.json --nome ingratidao_ep2 [--render]
Audio goes to output/minisserie/<nome>/, the project to motion/<nome>/, the video to output/minisserie/<nome>.mp4.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import bgm  # noqa: E402
import config  # noqa: E402
import novela_audio  # noqa: E402
import novela_hf  # noqa: E402
from novela_schema import Episodio  # noqa: E402

CLI = Path.home() / ".claude" / "skills" / "hyperframes" / "scripts" / "plugin-cli.mjs"


def hf(projeto: Path, *args: str) -> int:
    return subprocess.call(["node", str(CLI), *args], cwd=projeto)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roteiro")
    ap.add_argument("--nome", required=True)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--duracao", type=float, default=30.0, help="segundos (30 no aquecimento, 61 depois)")
    ap.add_argument("--sem-audio", action="store_true", help="reusa o timeline.json já gerado")
    args = ap.parse_args(argv)
    ep = Episodio.carregar(args.roteiro)
    pasta = config.OUTPUT / "minisserie" / args.nome
    timeline = pasta / "timeline.json"
    if not (args.sem_audio and timeline.exists()):
        r = novela_audio.gerar(ep, args.duracao, pasta, bgm=bgm.obter_bgm("tenso"))
        print(f"áudio ok (atempo {r.atempo:.3f})")
    projeto = RAIZ / "motion" / args.nome
    novela_hf.construir(ep, timeline, projeto)
    print(f"projeto: {projeto}")
    if hf(projeto, "check", "--json") != 0:
        print("check apontou problemas")
    if args.render:
        destino = config.OUTPUT / "minisserie" / f"{args.nome}.mp4"
        rc = hf(projeto, "render", "-q", "standard", "-o", str(destino))
        if rc:
            return rc
        import video_assembler as va

        print(va.conferir_video(destino))
    return 0


if __name__ == "__main__":
    sys.exit(main())
