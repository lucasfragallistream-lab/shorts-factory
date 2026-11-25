"""Ranking writer (phase R5): Gemini does the creative thinking, this module validates and retries.

    gerar(tema)        -> new Ranking for a theme (hook, items, CTA, emoji visuals, characters)
    revisar(ranking)   -> same ranking improved: stronger hook, CTA before the last item, visuals,
                          trimmed to the 61 s word budget, facts and items kept

Order: Gemini (config.GEMINI_MODEL, then the reserve models) -> optional OpenAI-compatible reserve
(LLM_FALLBACK_BASE_URL / LLM_FALLBACK_API_KEY / LLM_FALLBACK_MODEL) -> local fallback ranking.
Every answer is validated by schemas.Ranking plus `verificar` (TTS and duration rules); problems go
back to the model as feedback, up to TENTATIVAS times.
"""
from __future__ import annotations

import json
import os
import random
import re
import unicodedata
import urllib.request
from dataclasses import dataclass

from pydantic import ValidationError

import config
from schemas import Ranking, listar_fallbacks

TENTATIVAS = 3


class ErroRoteiro(RuntimeError):
    pass


def orcamento_palavras() -> tuple[int, int]:
    pps = config.NARRADOR["palavras_por_segundo"]
    # the words/s estimate ignores punctuation pauses, so aim ~1 s under the window (avoids atempo)
    return round(pps * (config.FALA_ALVO_MIN - 1.0)), round(pps * (config.FALA_ALVO_MAX - 1.5))


_VOCAB = {
    "idade": config.IDADES, "sexo": config.SEXOS, "pele": config.PELES, "cabelo": config.CABELOS,
    "cor_cabelo": config.CORES_CABELO, "roupa": config.ROUPAS, "cor_roupa": config.CORES,
    "acessorios": config.ACESSORIOS, "expressao": config.EXPRESSOES,
}


def _regras() -> str:
    pmin, pmax = orcamento_palavras()
    vocab = "\n".join(f"- {k}: {', '.join(v)}" for k, v in _VOCAB.items())
    return f"""Você é o melhor roteirista brasileiro de vídeos curtos de curiosidades e rankings, especialista em
prender a atenção nos dois primeiros segundos e fazer o público assistir até o fim, comentar e compartilhar.
O vídeo é vertical, dura 61 segundos e é narrado por uma única voz sintética (TTS) em português do Brasil.
Na tela aparecem personagens genéricos em uma escada, um por item, com uma etiqueta curta.

ESTRUTURA (JSON):
{{"titulo": "AS 5 ... (caixa alta, com o número de itens, até 60 caracteres)",
 "layout": "escada",
 "abertura": "gancho falado",
 "visuais_abertura": [{{"palavra": "palavra exata da abertura", "emoji": "um emoji"}}],
 "itens": [{{"rotulo": "etiqueta curta, até 24 caracteres", "narracao": "...",
            "personagem": {{"idade": "...", "sexo": "...", "pele": "...", "cabelo": "...", "cor_cabelo": "...",
                           "roupa": "...", "cor_roupa": "...", "acessorios": ["..."], "expressao": "..."}},
            "visuais": [{{"palavra": "palavra exata da narração deste item", "emoji": "um emoji"}}],
            "imagem": "termo de busca em inglês para achar uma foto real deste item no Wikimedia Commons"}}],
 "cta": "pedido para seguir, curtir e comentar, dito antes do último item",
 "fechamento": "...",
 "palavra_chave": "UmaPalavra",
 "visuais_fechamento": [{{"palavra": "...", "emoji": "..."}}]}}

GANCHO (abertura, 18 a 28 palavras):
- Comece com o detalhe mais chocante, concreto e específico do vídeo, falando direto com "você".
- Abra uma lacuna de curiosidade sobre o primeiro lugar sem entregar o nome dele.
- Proibido: "fica até o final", "neste vídeo", "hoje eu vou", "você sabia", "olá", saudações.
ITENS:
- De 3 a 5 itens, do menos para o mais impressionante; o último é o primeiro lugar e é o mais forte.
- Em rankings numerados, rótulos como "5º Nome curto" até "1º Nome curto". Em progressões (idades, dias),
  use o marco ("13 anos", "Dia 5").
- Cada narração tem 25 a 38 palavras: um fato concreto com número ou detalhe visual, e termina com uma virada,
  comparação do dia a dia ou frase de efeito.
- Fatos reais e verificáveis. Se houver dúvida, use "segundo relatos" ou "dizem que". Nunca invente número.
RETENÇÃO (o público larga vídeo morno; cada segundo precisa de um motivo para continuar):
- Escreva com energia de quem conta um segredo chocante: verbos fortes, comparações com o dia a dia de quem assiste,
  números concretos que assustam, e pelo menos uma revelação inesperada ou virada por item.
- Cada item, menos o último, termina com uma ponte para o próximo que aumenta a aposta, variando a forma
  (exemplos de ideia, não copie: "e se isso te assustou, o próximo é pior", "mas nada se compara ao que vem agora").
- A tensão sobe item a item; o primeiro lugar é o mais chocante e a narração dele começa com impacto.
- Fale com "você": coloque quem assiste dentro da cena ("imagina você...", "se você estivesse lá...").
- Evite tom de enciclopédia, introduções lentas e frases mornas como "é interessante notar".
CTA (12 a 22 palavras): dito logo antes do último item. Peça as três coisas na mesma frase corrida: seguir o
perfil, curtir o vídeo e comentar se concorda com o ranking (use os verbos seguir, curtir, comentar e concordar), criando expectativa para o último item (em ranking numerado ele é o primeiro lugar; em progressão
é a última fase). Varie a frase e ligue ao tema, nada de texto genérico.
FECHAMENTO (14 a 24 palavras): desafio de atenção. Peça para comentar a palavra_chave para provar que assistiu
até o fim (a palavra aparece escrita normalmente na frase, sem caixa alta) e para seguir e curtir.
PALAVRA_CHAVE: uma única palavra, sem espaço, ligada ao vídeo e fácil de lembrar, de preferência o nome do
primeiro lugar ou o detalhe mais marcante.
IMAGEM: para cada item, um termo de busca em inglês que encontre uma foto real e reconhecível do assunto do item no
Wikimedia Commons (nome científico ou nome exato do objeto, lugar ou pessoa; para animais extintos, use
"reconstruction" ou "fossil"). Se o item for uma situação ou fase da vida sem foto real, use o objeto que melhor a
represente.

REGRAS DE TTS (obrigatórias, a voz fica robótica se quebrar):
- Frases corridas e naturais. Nada de listas com vírgula ("sentado, trabalhando, respirando").
- Nada de siglas nem palavras em caixa alta na narração; escreva por extenso.
- Números por extenso ("treze", "dois mil e dezessete", "quatrocentos milhões").
- Nunca duas frases seguidas com 3 palavras ou menos. Sem emojis, aspas, parênteses ou hashtags no texto falado.
DURAÇÃO: a fala inteira (abertura + itens + cta + fechamento) precisa durar entre 56 e 60 segundos na voz
sintética, o que costuma dar entre {pmin - 25} e {pmax} palavras; nomes e números por extenso deixam a fala mais
lenta, então nesses temas use menos palavras. A duração real é medida depois e você recebe o ajuste exato.

VISUAIS (emojis que aparecem na tela quando a palavra é falada, para prender o olho):
- 2 a 3 por item, 1 ou 2 na abertura e 1 no fechamento.
- "palavra" é uma única palavra que aparece literalmente no texto daquele trecho, de preferência um substantivo
  concreto (comida, objeto, animal, dinheiro, lugar). "emoji" é um único emoji comum (sem combinações de pessoas, bandeiras ou tons de pele) que representa essa palavra.
- Espalhe os visuais ao longo da fala, sem repetir emoji no mesmo item.

PERSONAGENS (genéricos, um por item, combinando com o assunto e variando idade, sexo e pele). Valores permitidos:
{vocab}
- acessorios: no máximo 3, sem repetir.

Responda só com o JSON, sem comentários."""


def _norm(txt: str) -> str:
    txt = unicodedata.normalize("NFD", txt.lower())
    return "".join(c for c in txt if c.isalnum() and not unicodedata.combining(c))


def _norm_frase(txt: str) -> str:
    """Lowercase, no accents, words separated by single spaces, leading space."""
    txt = unicodedata.normalize("NFD", txt.lower())
    txt = "".join(c if c.isalnum() else " " for c in txt if not unicodedata.combining(c))
    return " " + " ".join(txt.split())


def verificar(r: Ranking, palavras: bool = True) -> list[str]:
    """Rule problems that pydantic does not catch (word budget, TTS, visuals).

    `palavras=False` skips the word budget, used when the real narration length is measured instead.
    """
    pmin, pmax = orcamento_palavras()
    out = []
    if palavras and not (pmin <= r.palavras <= pmax):
        out.append(f"o texto falado tem {r.palavras} palavras; precisa ter entre {pmin} e {pmax}")
    if not re.search(rf"\b{len(r.itens)}\b", r.titulo):
        out.append(f"o título precisa conter o número {len(r.itens)}")
    if len({it.rotulo for it in r.itens}) != len(r.itens):
        out.append("os rótulos dos itens precisam ser diferentes")
    if not r.palavra_chave:
        out.append("falta a palavra_chave")
    elif _norm(r.palavra_chave) not in _norm_frase(r.fechamento).replace(" ", " "):
        out.append(f"o fechamento precisa conter a palavra_chave '{r.palavra_chave}'")
    if any(not it.imagem for it in r.itens):
        out.append("todo item precisa do termo de busca 'imagem'")
    if not r.cta:
        out.append("falta o cta antes do último item")
    else:
        c = _norm_frase(r.cta)
        faltam = [nome for nome, raizes in (("seguir", ("segu", "sig")), ("curtir", ("curt",)),
                                            ("comentar", ("coment",)), ("concordar", ("concord",)))
                  if not any(f" {x}" in c for x in raizes)]
        if faltam:
            out.append(f"o cta precisa pedir para seguir, curtir e comentar se concorda; faltou: {', '.join(faltam)}")
    for s in r.segmentos():
        if re.search(r"\b[A-Z]{2,}\b", s.texto):
            out.append(f"sigla ou caixa alta na fala: {s.texto[:60]}")
        frases = [f for f in re.split(r"[.!?]+", s.texto) if f.strip()]
        curtas = [len(f.split()) <= 3 for f in frases]
        if any(a and b for a, b in zip(curtas, curtas[1:])):
            out.append(f"duas frases curtas seguidas em: {s.texto[:60]}")
        palavras = {_norm(w) for w in s.texto.split()}
        for v in s.visuais:
            alvo = _norm(v.palavra)
            if not any(p.startswith(alvo) for p in palavras):
                out.append(f"visual '{v.palavra}' não aparece no texto do trecho {s.tipo}")
    try:
        import emoji_renderer as er
        if er.disponivel():
            ruins = [v.emoji for s in r.segmentos() for v in s.visuais if not er.suportado(v.emoji)]
            if ruins:
                out.append(f"troque estes emojis por outros mais comuns: {' '.join(ruins)}")
    except Exception:  # noqa: BLE001 - emoji check is a nicety
        pass
    return out


# --- model calls ------------------------------------------------------------------------------
def _modelos() -> list[str]:
    principal = os.environ.get("GEMINI_MODEL") or config.GEMINI_MODEL
    return [principal] + [m for m in config.GEMINI_MODELOS_RESERVA if m != principal]


def _gemini(prompt: str, modelo: str) -> str:
    from google import genai
    from google.genai import types

    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        raise ErroRoteiro("GEMINI_API_KEY não definida")
    cliente = genai.Client(api_key=chave)
    resp = cliente.models.generate_content(
        model=modelo, contents=prompt,
        config=types.GenerateContentConfig(system_instruction=_regras(), response_mime_type="application/json",
                                           temperature=0.9))
    return resp.text or ""


def _reserva_openai(prompt: str) -> str:
    base = os.environ["LLM_FALLBACK_BASE_URL"].rstrip("/")
    corpo = json.dumps({"model": os.environ.get("LLM_FALLBACK_MODEL", ""), "temperature": 0.9,
                        "response_format": {"type": "json_object"},
                        "messages": [{"role": "system", "content": _regras()},
                                     {"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request(f"{base}/chat/completions", data=corpo, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {os.environ.get('LLM_FALLBACK_API_KEY', '')}"})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 - URL set by the user
        return json.loads(r.read())["choices"][0]["message"]["content"]


def _extrair_json(txt: str) -> dict:
    txt = txt.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```\w*\s*|\s*```$", "", txt)
    ini, fim = txt.find("{"), txt.rfind("}")
    return json.loads(txt[ini:fim + 1])


MEDIR_FALA = True  # synthesize the real narration (edge, cached) to check it fits 61 s; tests turn it off
FALA_MAX = config.DURACAO_ALVO * 1.03  # narration + pauses may need at most ~3% speed-up


def duracao_fala_real(r: Ranking, motor=None) -> float:
    """Seconds the narration takes with the real voice, plus the minimum pauses of the timeline."""
    import voice_engine as ve

    motor = motor or ve.criar_motor(config.TTS_PADRAO)
    segs = r.segmentos()
    audios = motor.sintetizar_lote([(s.texto, ve.voz_narrador()) for s in segs])
    gaps = len(segs) - 1
    return ve.INICIO_PADRAO + sum(a.duracao for a in audios) + gaps * ve.PAUSA_MIN + ve.RESPIRO_MIN


def checar_fala_real(r: Ranking, log) -> list[str]:
    try:
        seg = duracao_fala_real(r)
    except Exception as exc:  # noqa: BLE001 - offline: keep the word-count estimate
        log(f"não deu para medir a fala real ({type(exc).__name__}); seguindo pela contagem de palavras")
        pmin, pmax = orcamento_palavras()
        return [] if pmin <= r.palavras <= pmax else [f"o texto falado tem {r.palavras} palavras; precisa ter "
                                                       f"entre {pmin} e {pmax}"]
    pps = config.NARRADOR["palavras_por_segundo"]
    if seg > FALA_MAX:
        cortar = max(6, round((seg - config.DURACAO_ALVO + 1.0) * pps))
        return [f"a narração real ficou com {seg:.1f} s e passa de 61 s; corte cerca de {cortar} palavras, "
                "de preferência números longos por extenso e frases secundárias"]
    if seg < config.DURACAO_MINIMA - 4:
        crescer = round((config.DURACAO_MINIMA - 2 - seg) * pps)
        return [f"a narração real ficou com só {seg:.1f} s; acrescente cerca de {crescer} palavras"]
    return []


@dataclass
class Resultado:
    ranking: Ranking
    origem: str  # model name, "reserva" or "fallback:NOME"
    tentativas: int
    problemas: list[str]


def _com_retentativas(pedido: str, chamar, origem: str, log) -> Resultado | None:
    prompt = pedido
    ultimo: list[str] = []
    for n in range(1, TENTATIVAS + 1):
        try:
            dados = _extrair_json(chamar(prompt))
            r = Ranking.model_validate(dados)
            ultimo = verificar(r, palavras=not MEDIR_FALA)
            if not ultimo and MEDIR_FALA:
                ultimo = checar_fala_real(r, log)
        except (ValueError, ValidationError) as exc:
            dados, r = None, None
            ultimo = [f"JSON inválido ou fora do schema: {str(exc)[:600]}"]
        log(f"{origem} tentativa {n}: " + ("ok" if not ultimo else "; ".join(ultimo)[:300]))
        if r is not None and not ultimo:
            return Resultado(r, origem, n, [])
        anterior = json.dumps(dados, ensure_ascii=False) if dados else "(resposta inválida)"
        prompt = (f"{pedido}\n\nSua resposta anterior foi:\n{anterior}\n\nCorrija estes problemas e responda o "
                  f"JSON completo de novo:\n- " + "\n- ".join(ultimo))
    return None


def _executar(pedido: str, log) -> Resultado | None:
    for modelo in _modelos():
        try:
            res = _com_retentativas(pedido, lambda p, m=modelo: _gemini(p, m), modelo, log)
        except ErroRoteiro:
            raise
        except Exception as exc:  # noqa: BLE001 - API/network errors: try the next model
            log(f"{modelo} falhou: {type(exc).__name__}: {str(exc)[:200]}")
            continue
        if res is not None:
            return res
    if os.environ.get("LLM_FALLBACK_BASE_URL"):
        try:
            return _com_retentativas(pedido, _reserva_openai, "reserva", log)
        except Exception as exc:  # noqa: BLE001
            log(f"reserva falhou: {type(exc).__name__}: {str(exc)[:200]}")
    return None


def gerar(tema: str, n_itens: int | None = None, seed: int | None = None, log=print) -> Resultado:
    """New ranking for `tema`; falls back to a local ranking if every model fails."""
    pedido = f"Crie um ranking viral sobre o tema: {tema}."
    if n_itens:
        pedido += f" Use exatamente {n_itens} itens."
    try:
        res = _executar(pedido, log)
    except ErroRoteiro as exc:
        log(f"roteirista indisponível: {exc}")
        res = None
    if res is not None:
        return res
    nome = random.Random(seed).choice(listar_fallbacks())
    log(f"usando ranking local de fallback: {nome}")
    return Resultado(Ranking.carregar(config.RANKINGS / f"{nome}.json"), f"fallback:{nome}", 0, [])


def revisar(r: Ranking, log=print) -> Resultado | None:
    """Ask the model to improve an existing ranking (hook, CTA, visuals, word budget), keeping its items."""
    atual = r.model_dump_json(exclude_none=True)
    pedido = ("Revise este ranking existente. Mantenha o tema, o título, os mesmos itens na mesma ordem, os rótulos, "
              "os personagens e os fatos. Mantenha o gancho atual se ele já for forte e específico; só reescreva "
              "se estiver fraco, genérico ou entregar o primeiro lugar. "
              "escreva o cta, adicione os visuais e ajuste o tamanho das narrações para caber no total de palavras. "
              f"Ranking atual:\n{atual}")
    return _executar(pedido, log)
