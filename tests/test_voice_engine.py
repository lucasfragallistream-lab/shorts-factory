import json

import numpy as np
import pytest

import config
import voice_engine as ve
from schemas import Ranking, listar_fallbacks


# --- duration planning ------------------------------------------------------
def _total(plano, duracoes):
    d = [x / plano.atempo for x in duracoes]
    return plano.inicio + sum(d) + sum(plano.pausas) + plano.respiro


@pytest.mark.parametrize("fala_total", [40.0, 55.0, 57.0, 59.0, 60.0, 61.0, 62.5])
def test_plano_sempre_fecha_no_alvo(fala_total):
    duracoes = [fala_total / 10] * 10
    plano = ve.planejar_duracao(duracoes, 61.0)
    assert _total(plano, duracoes) == pytest.approx(61.0, abs=1e-3)
    assert plano.respiro >= ve.RESPIRO_MIN - 1e-6
    assert 1.0 <= plano.atempo <= ve.ATEMPO_MAX
    assert all(ve.PAUSA_MIN - 1e-6 <= p <= config.PAUSA_ENTRE_SEGMENTOS + ve.PAUSA_EXTRA_MAX + 1e-6
               for p in plano.pausas)


def test_plano_curto_aumenta_pausa_e_respiro():
    plano = ve.planejar_duracao([5.0] * 10, 61.0)
    assert plano.pausas[0] == pytest.approx(config.PAUSA_ENTRE_SEGMENTOS + ve.PAUSA_EXTRA_MAX)
    assert plano.respiro > 4 and plano.atempo == 1.0


def test_plano_longo_usa_atempo():
    plano = ve.planejar_duracao([6.2] * 10, 61.0)
    assert plano.atempo > 1.0 and plano.pausas[0] == ve.PAUSA_MIN


def test_plano_longo_demais_falha():
    with pytest.raises(ve.ErroDuracao, match="encurte"):
        ve.planejar_duracao([7.0] * 10, 61.0)


def test_trava_60s():
    with pytest.raises(ve.ErroDuracao):
        ve.planejar_duracao([5.0] * 10, 59.0)


# --- lip-sync helpers -------------------------------------------------------
def test_rms_por_frame():
    sinal = np.concatenate([np.zeros(ve.SR // 30), 0.5 * np.ones(ve.SR // 30)]).astype(np.float32)
    rms = ve.rms_por_frame(sinal, 2)
    assert rms[0] == 0 and rms[1] == pytest.approx(0.5, abs=1e-3)


def test_energia_suave_normalizada():
    rms = np.array([0, 0, 0.2, 0.4, 0.4, 0.4, 0], np.float32)
    e = ve.energia_suave(rms)
    assert e.min() >= 0 and e.max() <= 1 and e[0] == 0 and e[4] > 0.5


# --- engines ---------------------------------------------------------------
def test_mock_deterministico_e_aparado():
    m = ve.MotorMock()
    a = m.sintetizar("Olá, tudo bem? Sim.", ve.voz_narrador())
    b = m.sintetizar("Olá, tudo bem? Sim.", ve.voz_narrador())
    assert np.array_equal(a.amostras, b.amostras)
    assert len(a.palavras) == 4 and not np.isnan(a.amostras).any()
    assert a.palavras[0].inicio == pytest.approx(ve.MARGEM_INICIO, abs=1e-3)
    assert a.duracao == pytest.approx(a.palavras[-1].fim + ve.MARGEM_FIM, abs=2e-3)


def test_edge_usa_cache_sem_rede(tmp_path, monkeypatch):
    motor = ve.MotorEdge(tmp_path)
    voz = ve.voz_narrador()
    mp3, wav, js = motor._arquivos("oi gente", voz)
    ve.salvar_wav(wav, 0.1 * np.ones(ve.SR, np.float32))
    js.write_text(json.dumps([{"texto": "oi", "inicio": 0.2, "fim": 0.4},
                              {"texto": "gente", "inicio": 0.45, "fim": 0.8}]), encoding="utf-8")

    async def sem_rede(*a, **k):
        raise AssertionError("não deveria acessar a rede")

    monkeypatch.setattr(motor, "_baixar", sem_rede)
    audio = motor.sintetizar("oi gente", voz)
    assert audio.duracao == pytest.approx(0.8 + ve.MARGEM_FIM - (0.2 - ve.MARGEM_INICIO), abs=1e-3)
    assert [p.texto for p in audio.palavras] == ["oi", "gente"]


def test_chave_cache_muda_com_voz():
    v = ve.voz_narrador()
    assert ve._chave("edge", "oi", v) != ve._chave("edge", "oi", {**v, "pitch": "+1Hz"})
    assert ve._chave("edge", "oi", v) != ve._chave("edge", "oi!", v)


def test_criar_motor_invalido():
    with pytest.raises(ValueError):
        ve.criar_motor("kokoro")


def test_atempo_encurta(tmp_path):
    a = ve.MotorMock().sintetizar("teste de velocidade da fala", ve.voz_narrador())
    b = ve.aplicar_atempo(a, 1.08)
    assert b.duracao == pytest.approx(a.duracao / 1.08, abs=0.03)
    assert b.palavras[-1].fim == pytest.approx(a.palavras[-1].fim / 1.08, abs=1e-3)


# --- whole episode ---------------------------------------------------------
@pytest.mark.parametrize("nome", listar_fallbacks())
def test_gerar_audio_mock(nome, tmp_path):
    r = Ranking.carregar(config.RANKINGS / f"{nome}.json")
    res = ve.gerar_audio(r, ve.MotorMock(), 61.0, tmp_path / "v.wav", tmp_path / "t.json")
    assert len(ve.ler_wav(res.wav)) == 61 * ve.SR
    t = json.loads(res.timeline.read_text(encoding="utf-8"))
    assert t["versao"] == 2 and t["frames"] == 1830
    assert len(t["item_atual"]) == 1830 and len(t["energia"]) == 1830
    segs = t["segmentos"]
    assert [s["tipo"] for s in segs] == [s.tipo for s in r.segmentos()]
    assert [s["rotulo"] for s in segs if s["tipo"] == "item"] == [it.rotulo for it in r.itens]
    assert segs[-1]["fim"] <= 61.0 - ve.RESPIRO_MIN + 1e-3
    assert [s["inicio"] for s in segs] == sorted(s["inicio"] for s in segs)
    assert all(s["palavras"] for s in segs)
    ia = t["item_atual"]
    assert ia[0] == -1 and ia[-1] == len(r.itens)
    so_itens = [v for v in ia if 0 <= v < len(r.itens)]
    assert so_itens == sorted(so_itens)  # items appear in order, never go back (cta frames are marked n)
    for s in segs:
        if s["tipo"] == "item":
            assert ia[s["frame_inicio"]] == s["item"]
        elif s["tipo"] == "cta":
            assert ia[s["frame_inicio"]] == len(r.itens)
    assert t["ranking"]["titulo"] == r.titulo and t["layout"] == r.layout


def test_medir_palavras_por_segundo_mock():
    rs = [Ranking.carregar(config.RANKINGS / f"{n}.json") for n in listar_fallbacks()]
    assert 1.5 < ve.medir_palavras_por_segundo(rs, ve.MotorMock()) < 5
