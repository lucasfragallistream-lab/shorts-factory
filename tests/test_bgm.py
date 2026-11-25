import wave

import numpy as np
import pytest

import bgm
import config


@pytest.mark.parametrize("estilo", ["leve", "tenso"])
def test_gerar_trilha(estilo, tmp_path):
    p = bgm.gerar(estilo, tmp_path / "t.wav", duracao=8.0, seed=1)
    with wave.open(str(p)) as w:
        assert w.getframerate() == bgm.SR
        a = np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32768
    assert len(a) == 8 * bgm.SR
    assert 0.03 < np.sqrt(np.mean(a ** 2)) < 0.3 and np.abs(a).max() <= 0.96


def test_trilhas_diferentes_por_estilo(tmp_path):
    a = bgm.gerar("leve", tmp_path / "a.wav", duracao=4.0).read_bytes()
    b = bgm.gerar("tenso", tmp_path / "b.wav", duracao=4.0).read_bytes()
    assert a != b


def test_bgm_do_usuario_tem_prioridade(tmp_path, monkeypatch):
    meu = tmp_path / "bgm.mp3"
    meu.write_bytes(b"x")
    monkeypatch.setattr(config, "BGM", meu)
    assert bgm.obter_bgm() == meu


def test_bgm_gerada_em_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BGM", tmp_path / "nao_existe.mp3")
    monkeypatch.setattr(config, "CACHE", tmp_path)
    monkeypatch.setattr(bgm, "DURACAO_PADRAO", 3.0)
    p = bgm.obter_bgm("tenso", seed=3)
    assert p.exists() and p.parent == tmp_path / "bgm"


def test_estilo_invalido(tmp_path):
    with pytest.raises(ValueError):
        bgm.gerar("idiota", tmp_path / "x.wav")
