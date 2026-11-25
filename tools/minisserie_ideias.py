"""Ask Gemini for pilot-episode pitches of an emotional vertical miniseries (novela / real-life drama).

Usage: python tools/minisserie_ideias.py [--n 3]
Prints the pitches and saves them to output/minisserie/ideias.json.
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

PEDIDO = """Você é roteirista-chefe de minisséries verticais virais brasileiras (estilo novela e dramas da vida real)
para TikTok, Reels e Shorts. Cada episódio dura 61 segundos, tem narrador e falas de personagens com vozes
sintéticas, cenários simples (casa, cozinha, quarto, carro, hospital, escritório) e termina num gancho que obriga
a ver o próximo episódio.

Crie {n} propostas de minissérie, bem diferentes entre si:
- uma de amor e traição (novela),
- uma de filhos que maltratam ou abandonam os pais que sempre cuidaram deles,
- uma livre, também emocional (escolha o tema que mais prende o público brasileiro).

Regras: personagens originais e genéricos, sem nomes de famosos. Nada de violência gráfica ou conteúdo sexual.
Emoção forte (injustiça, revelação, reviravolta), com um gancho visual no primeiro segundo.

Responda só com JSON: {{"ideias": [{{"titulo_serie": "...", "tema": "...", "titulo_ep1": "título curto e chocante
para o 1º quadro", "gancho_1s": "o que aparece e é dito no primeiro segundo", "enredo_ep1": "5 a 7 frases com o que
acontece no episódio 1, cena por cena", "cliffhanger": "como o episódio 1 termina", "personagens": ["nome (idade,
papel)"], "cenarios": ["..."], "proximos": "1 frase sobre o que vem nos episódios 2 e 3",
"pergunta_comentarios": "pergunta que divide opiniões para o fim"}}]}}"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args(argv)
    from google import genai
    from google.genai import types
    import os

    cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    erro = None
    for modelo in sg._modelos():
        try:
            resp = cliente.models.generate_content(
                model=modelo, contents=PEDIDO.format(n=args.n),
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0))
            dados = sg._extrair_json(resp.text or "")
            break
        except Exception as exc:  # noqa: BLE001 - try the next model
            erro = exc
    else:
        raise SystemExit(f"Gemini indisponível: {erro}")
    destino = config.OUTPUT / "minisserie" / "ideias.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
