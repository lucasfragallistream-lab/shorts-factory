import json

import pytest

import config
import emoji_renderer as er
import script_generator as sg
from schemas import Ranking


def _crises(**extra) -> Ranking:
    d = json.loads((config.RANKINGS / "crises.json").read_text(encoding="utf-8"))
    d.update(extra)
    return Ranking.model_validate(d)


def test_extrair_json_com_cerca():
    assert sg._extrair_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert sg._extrair_json('texto {"b": [1, 2]} fim') == {"b": [1, 2]}


def test_verificar_aponta_problemas():
    r = _crises(cta=None, abertura="Veja o RH. Muito bom. Sim mesmo.")
    probs = " | ".join(sg.verificar(r))
    assert "cta" in probs and "sigla" in probs and "curtas" in probs


def test_verificar_visual_fora_do_texto():
    d = json.loads((config.RANKINGS / "crises.json").read_text(encoding="utf-8"))
    d["itens"][0]["visuais"] = [{"palavra": "foguete", "emoji": "🚀"}]
    assert any("foguete" in p for p in sg.verificar(Ranking.model_validate(d)))


def test_gerar_sem_chave_cai_no_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_FALLBACK_BASE_URL", raising=False)
    res = sg.gerar("tema qualquer", seed=1, log=lambda m: None)
    assert res.origem.startswith("fallback:") and isinstance(res.ranking, Ranking)


def test_retentativa_com_feedback(monkeypatch):
    bom = (config.RANKINGS / "crises.json").read_text(encoding="utf-8")
    respostas = iter(["isto não é json", bom])
    prompts = []

    def falso(prompt, modelo):
        prompts.append(prompt)
        return next(respostas)

    monkeypatch.setattr(sg, "_gemini", falso)
    monkeypatch.setattr(sg, "MEDIR_FALA", False)
    monkeypatch.setattr(sg, "verificar", lambda r, **kw: [])
    res = sg._executar("pedido", lambda m: None)
    assert res is not None and res.tentativas == 2 and "Corrija" in prompts[1]


def test_segmentos_com_cta_antes_do_ultimo():
    r = _crises(cta="Segue o perfil, curte e comenta se concorda antes da última crise da lista.")
    tipos = [s.tipo for s in r.segmentos()]
    assert tipos == ["abertura", "item", "item", "item", "cta", "item", "fechamento"]


def test_regras_tem_orcamento():
    pmin, pmax = sg.orcamento_palavras()
    assert f"e {pmax} palavras" in sg._regras()


@pytest.mark.skipif(not er.disponivel(), reason="sem fonte de emoji")
def test_emoji_adesivo():
    a = er.adesivo("🎓", 200)
    assert a is not None and a.mode == "RGBA" and a.width > 200
    assert not er.suportado("👨‍👩‍👦")  # ZWJ family draws as several glyphs


def test_checar_fala_real_pede_corte(monkeypatch):
    monkeypatch.setattr(sg, "duracao_fala_real", lambda r: 68.2)
    probs = sg.checar_fala_real(_crises(), lambda m: None)
    assert probs and "corte cerca de" in probs[0]
    monkeypatch.setattr(sg, "duracao_fala_real", lambda r: 59.0)
    assert sg.checar_fala_real(_crises(), lambda m: None) == []
