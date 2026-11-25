import numpy as np
import pytest

import config
import sfx
from montagem import Montagem
from schemas import Ranking


@pytest.mark.parametrize("tipo", sfx.TIPOS)
def test_sons_existem_e_tem_nivel(tipo):
    s = sfx.som(tipo)
    assert s.dtype == np.float32 and len(s) > 1000
    assert abs(20 * np.log10(np.max(np.abs(s))) - sfx.NIVEL_DB) < 0.1


def test_trilha_posiciona_e_corta():
    tr = sfx.trilha_sfx([sfx.EventoSom(1.0, "pop"), sfx.EventoSom(9.99, "impacto")], 10.0)
    assert len(tr) == 10 * sfx.SR
    assert np.max(np.abs(tr[: int(0.99 * sfx.SR)])) == 0  # nothing before the pop
    assert np.max(np.abs(tr[sfx.SR: sfx.SR + 2000])) > 0


def test_subida_termina_no_instante():
    tr = sfx.trilha_sfx([sfx.EventoSom(5.0, "subida")], 8.0)
    assert np.max(np.abs(tr[int(5.01 * sfx.SR):])) == 0 and np.max(np.abs(tr[int(4.5 * sfx.SR):int(5 * sfx.SR)])) > 0


def test_mapa_de_sons_e_slam(timeline_mock):
    _, tl = timeline_mock
    m = Montagem(Ranking.carregar(config.RANKINGS / "crises.json"), tl)
    tipos = [e.tipo for e in m.eventos_sonoros()]
    assert tipos.count("impacto") >= len(m.inicio_item) and "subida" in tipos
    assert m._texto_slam(0) == "13 ANOS"
    ini = m.inicio_item[m.n - 1]
    img = m.quadro(int((ini + 0.1) * m.fps))  # slam + flash + alarm on the last item
    assert img.size == (config.LARGURA, config.ALTURA)


def test_slam_ordinal():
    from montagem import Montagem as M

    class Falso:
        class r:
            itens = [type("I", (), {"rotulo": "5º Pasta de amendoim"})(), type("I", (), {"rotulo": "Dia 12"})()]

    assert M._texto_slam(Falso, 0) == "5º"
    assert M._texto_slam(Falso, 1) == "DIA 12"
