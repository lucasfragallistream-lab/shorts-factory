"""Ask Gemini to revise local rankings (hook, CTA before the last item, emoji visuals, word budget).

Usage: python tools/revisar_rankings.py [NOME ...] [--gravar]
Without --gravar the revised JSON goes to output/rankings/revisado_NOME.json for review.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
import script_generator as sg  # noqa: E402
from schemas import Ranking, listar_fallbacks  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("nomes", nargs="*")
    ap.add_argument("--gravar", action="store_true", help="sobrescreve assets/rankings/NOME.json")
    ap.add_argument("--pendentes", action="store_true",
                    help="só os que falham nas regras ou cuja fala real (voz edge) não cabe em 61 s")
    args = ap.parse_args(argv)
    falhas = 0
    for nome in args.nomes or listar_fallbacks():
        caminho = config.RANKINGS / f"{nome}.json"
        log = lambda m, n=nome: print(f"[{n}] {m}", flush=True)  # noqa: E731
        if args.pendentes:
            atual = Ranking.carregar(caminho)
            probs = sg.verificar(atual, palavras=False) or sg.checar_fala_real(atual, log)
            if not probs:
                log("ok, nada a revisar")
                continue
            log("revisando: " + "; ".join(probs)[:200])
        res = sg.revisar(Ranking.carregar(caminho), log=log)
        if res is None:
            falhas += 1
            log("FALHOU, mantido o original")
            continue
        dados = res.ranking.model_dump(exclude_none=True)
        destino = caminho if args.gravar else config.RANKINGS_GERADOS / f"revisado_{nome}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"ok ({res.ranking.palavras} palavras, {res.origem}, {res.tentativas} tentativa(s)) -> {destino.name}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
