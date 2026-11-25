"""Gemini writes one miniseries episode (novela_schema.Episodio) from a chosen pitch in output/minisserie/ideias.json.

Usage: python tools/novela_roteiro.py --ideia 2 [--episodio 1]
Writes output/minisserie/<serie>_ep<N>.json. Validates the schema and the word budget, retries with feedback.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
import script_generator as sg  # noqa: E402
from novela_schema import CENARIOS, Episodio  # noqa: E402

DURACAO = 30  # account warm-up phase: short episodes for retention (61 s again when monetizing)


def metas(duracao: int) -> dict:
    """Script targets scaled to the video length (Edge voices with pauses speak ~2.4 words/s)."""
    curto = duracao <= 40
    return {"pmin": round(duracao * 2.0), "pmax": round(duracao * 2.35),
            "cenas": "1 a 2" if curto else "3 a 4", "falas": "6 a 9" if curto else "12 a 20",
            "narr": 2 if curto else 4, "dest": "2 a 3" if curto else "3 a 6",
            "acoes": (1, 3) if curto else (3, 6)}


def regras(duracao: int = DURACAO) -> str:
    m = metas(duracao)
    a0, a1 = m["acoes"]
    return f"""Você é roteirista-chefe de minisséries verticais virais brasileiras (novela e dramas da vida real).
Escreva o EPISÓDIO pedido como JSON no formato abaixo. Duração: {duracao} segundos falados por vozes sintéticas.

FORMATO:
{{"serie": "...", "numero": 1, "titulo": "frase curta e chocante para o primeiro quadro (até 45 caracteres)",
 "elenco": [{{"id": "lurdes", "nome": "Dona Lurdes", "papel": "protagonista|vilao|vila|aliado|misterio",
   "personagem": {{"idade": "crianca|adolescente|jovem|adulto|meia_idade|idoso", "sexo": "masculino|feminino",
     "pele": "clara|media|morena|negra", "cabelo": "curto|espetado|liso|cacheado|comprido|coque|rabo|careca",
     "cor_cabelo": "preto|castanho|loiro|ruivo|grisalho|branco", "roupa": "camiseta|moletom|camisa|social|vestido|jaqueta",
     "cor_roupa": "azul|azul_claro|vermelho|verde|amarelo|roxo|laranja|rosa|cinza|preto|branco|bege",
     "acessorios": ["oculos|barba|bigode|caneca|mochila|fone|gravata|celular|bone|bengala|sacola|colar"],
     "expressao": "feliz|preocupado|cansado|chocado"}}}}],
 "cenas": [{{"cenario": "{'|'.join(CENARIOS)}", "chuva": false, "presentes": ["ids da esquerda para a direita"],
   "falas": [{{"quem": "narrador ou id", "texto": "...", "emocao": "neutra|triste|chorando|raiva|deboche|choque|medo|esperanca",
     "enquadramento": "close|medio|geral", "destaque": "1 a 3 palavras que aparecem gigantes na tela, ou null",
     "gesto": "aponta|estende|bracos_cima|maos_rosto|maos_cintura|mao_peito ou null",
     "acao": "aproxima|empurra|abraca|entra|sai ou null", "alvo": "id de quem recebe o gesto/ação, ou null"}}],
   "objetos": ["malas|carro_luxo (opcional)"]}}],
 "pergunta": "pergunta que divide opiniões, mostrada no fim", "proximo": "PARTE 3",
 "momento_chave": {{"cena": 0, "fala": 0, "prompt": "in English: the single most shocking moment, described as
   motion for an image-to-video model animating a flat 2D cartoon frame (who moves, how, camera move), 1-2 sentences"}}}}

REGRAS DE ROTEIRO:
- Total de {m["pmin"]} a {m["pmax"]} palavras faladas (obrigatório). De {m["cenas"]} cenas, de {m["falas"]} falas.
- Primeira fala: o narrador lança o gancho em uma frase forte (o que de pior acontece no episódio), em até 2 segundos.
- Episódio curto = retenção: zero enrolação, cada fala é um conflito, o clímax chega antes da metade e o fim corta
  seco numa frase que faz a pessoa querer ver de novo ou ir para a próxima parte.
- Mostre, não explique: a maior parte do episódio são falas dos personagens, curtas e cheias de emoção; o narrador
  só costura (no máximo {m["narr"]} falas do narrador).
- Ritmo de novela: injustiça clara, frases que dão raiva no público, uma virada, e o episódio CORTA no clímax.
- Gancho: UMA frase construída numa contradição ou ação estranha ("Ele vendeu a casa com a mãe dentro"), sem introdução.
- Detalhes pequenos e exatos ("três anos", "às seis da manhã"), não estatísticas; cresça em três ("Uma mala. Depois
  outra. Depois a vida inteira dela na chuva.").
- Arco: humilhação clara, piora, virada, e quem humilhou paga (carma) ou fica sem palavras.
- Espinha causal: cada fala causa a próxima (por isso..., então...), nada solto. O fim retoma a emoção ou a
  imagem do começo (ex.: as malas, a chuva, o retrato) com sentido virado.
- A última fala é o cliffhanger, dita pelo personagem do mistério ou pelo narrador, e fica sem resposta.
- Use "close" nas falas de maior emoção, "geral" quando a cena começa, "medio" no resto.
- "destaque" em {m["dest"]} falas-chave (ex.: "VENDI A CASA", "DÍVIDAS DE JOGO"), nunca em todas.
- Regras de voz sintética: frases naturais e corridas, sem siglas, números por extenso, sem reticências seguidas,
  sem onomatopeias, sem emojis.
- INTERAÇÃO (obrigatório): os personagens se movem e se tocam. Use "acao" em {a0} a {a1} falas: alguém se aproxima
  para confrontar, empurra, abraça, entra de repente ou sai batendo o pé. "alvo" é o id de quem recebe. "gesto" é
  opcional (se null, o gesto sai da emoção). Personagens que entram depois precisam estar em "presentes" da cena.
- "momento_chave": o momento mais chocante do episódio (índices de cena e fala, contando do zero).
- Personagens originais e genéricos. Nada de violência gráfica (um empurrão é o limite).
Responda só com o JSON."""


def _gerar(pedido: str, duracao: int = DURACAO) -> Episodio:
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt, ultimo = pedido, []
    for tentativa in range(1, 4):
        for modelo in sg._modelos():
            try:
                resp = cliente.models.generate_content(
                    model=modelo, contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=regras(duracao), temperature=0.9,
                                                       response_mime_type="application/json"))
                texto = resp.text or ""
                break
            except Exception as exc:  # noqa: BLE001 - next model
                print(f"{modelo} falhou: {str(exc)[:120]}")
        else:
            raise SystemExit("Gemini indisponível")
        try:
            dados = sg._extrair_json(texto)
            ep = Episodio.model_validate(dados)
            ultimo = []
            m = metas(duracao)
            if not m["pmin"] <= ep.palavras <= m["pmax"]:
                ultimo.append(f"o episódio tem {ep.palavras} palavras faladas; precisa ter entre {m['pmin']} e "
                              f"{m['pmax']}")
            acoes = sum(1 for c in ep.cenas for f in c.falas if f.acao)
            if acoes < m["acoes"][0]:
                ultimo.append(f"só {acoes} falas com 'acao'; use de {m['acoes'][0]} a {m['acoes'][1]} "
                              "(aproxima, empurra, abraca, entra, sai)")
            if ep.momento_chave is None:
                ultimo.append("falta o 'momento_chave'")
            for c in ep.cenas:
                for f in c.falas:
                    if re.search(r"\b[A-Z]{2,}\b", f.texto):
                        ultimo.append(f"sigla ou caixa alta na fala: {f.texto[:50]}")
        except Exception as exc:  # noqa: BLE001
            dados, ultimo = None, [f"JSON inválido: {str(exc)[:500]}"]
        print(f"tentativa {tentativa}: " + ("ok" if not ultimo else "; ".join(ultimo)[:300]))
        if not ultimo:
            return ep
        prompt = (f"{pedido}\n\nSua resposta anterior:\n{json.dumps(dados, ensure_ascii=False) if dados else '-'}"
                  f"\n\nCorrija e responda o JSON completo:\n- " + "\n- ".join(ultimo))
    raise SystemExit("não consegui um episódio válido em 3 tentativas")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ideia", type=int, required=True, help="número da ideia em ideias.json (1, 2, 3)")
    ap.add_argument("--episodio", type=int, default=1)
    ap.add_argument("--anterior", help="JSON do episódio anterior (continuidade)")
    ap.add_argument("--duracao", type=int, default=DURACAO, help="segundos do vídeo (30 no aquecimento, 61 depois)")
    args = ap.parse_args(argv)
    pasta = config.OUTPUT / "minisserie"
    ideia = json.loads((pasta / "ideias.json").read_text(encoding="utf-8"))["ideias"][args.ideia - 1]
    pedido = (f"Escreva o episódio {args.episodio} desta minissérie:\n{json.dumps(ideia, ensure_ascii=False)}")
    if args.anterior:
        ant = json.loads(Path(args.anterior).read_text(encoding="utf-8"))
        pedido += ("\n\nEpisódio anterior (continue exatamente de onde parou, mesmo elenco com os mesmos ids e "
                   "aparência; o gancho do narrador relembra o cliffhanger em uma frase):\n"
                   + json.dumps(ant, ensure_ascii=False))
    ep = _gerar(pedido, args.duracao)
    import unicodedata

    sem_acento = unicodedata.normalize("NFKD", ep.serie).encode("ascii", "ignore").decode().lower()
    nome = re.sub(r"[^a-z0-9]+", "_", sem_acento).strip("_")[:30] or "serie"
    destino = pasta / f"{nome}_ep{ep.numero}.json"
    destino.write_text(json.dumps(ep.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{destino} | {ep.palavras} palavras | {sum(len(c.falas) for c in ep.cenas)} falas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
