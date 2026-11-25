import re

import pytest

import config
from schemas import Ranking, listar_fallbacks


@pytest.mark.parametrize("nome", listar_fallbacks())
def test_ranking_fallback(nome):
    r = Ranking.carregar(config.RANKINGS / f"{nome}.json")
    assert config.ITENS_MIN <= len(r.itens) <= config.ITENS_MAX
    assert re.search(rf"\b{len(r.itens)}\b", r.titulo), "o título traz o número de itens (ex.: AS 4 CRISES)"
    # words/s varies a lot with names and spelled-out numbers: the real fit is checked on the real audio
    # (script_generator.checar_fala_real); here only a coarse sanity window
    assert 38.0 <= r.duracao_fala_estimada() <= 66.0
    assert len({it.rotulo for it in r.itens}) == len(r.itens)


@pytest.mark.parametrize("nome", listar_fallbacks())
def test_frases_corridas_para_tts(nome):
    """TTS rule (plan R1/Phase 5): no all-caps acronyms and no runs of very short sentences."""
    r = Ranking.carregar(config.RANKINGS / f"{nome}.json")
    for s in r.segmentos():
        assert not re.search(r"\b[A-Z]{2,}\b", s.texto), s.texto
        frases = [f for f in re.split(r"[.!?]+", s.texto) if f.strip()]
        curtas = [len(f.split()) <= 3 for f in frases]
        assert not any(a and b for a, b in zip(curtas, curtas[1:])), s.texto


@pytest.mark.parametrize("nome", listar_fallbacks())
def test_retencao_cta_e_visuais(nome):
    """User rule (20/11/2026): CTA before the last item and on-screen emojis tied to spoken words."""
    r = Ranking.carregar(config.RANKINGS / f"{nome}.json")
    assert r.cta
    assert all(it.visuais for it in r.itens)
    assert "fica até o final" not in r.abertura.lower()


def test_config_formato():
    assert (config.LARGURA, config.ALTURA, config.FPS) == (1080, 1920, 30)
    assert round(config.DURACAO_ALVO * config.FPS) == 1830
    assert config.DURACAO_MINIMA == 60.0
