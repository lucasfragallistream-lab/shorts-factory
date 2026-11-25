import pytest

import config
import figure_renderer as fr
import layout_renderer as lr
from schemas import Personagem, Ranking, listar_fallbacks


@pytest.mark.parametrize("idade", config.IDADES)
@pytest.mark.parametrize("expressao", config.EXPRESSOES)
def test_figura_idades_expressoes(idade, expressao):
    img = fr.renderizar(Personagem(idade=idade), 300, expressao)
    assert img.mode == "RGBA" and img.height == 300
    assert img.getbbox() is not None


def test_figura_todos_acessorios_e_roupas():
    for roupa in config.ROUPAS:
        for cab in config.CABELOS:
            for i in range(0, len(config.ACESSORIOS), 3):
                p = Personagem(roupa=roupa, cabelo=cab, acessorios=list(config.ACESSORIOS[i:i + 3]))
                assert fr.renderizar(p, 120, boca="aberta", piscando=True).getbbox()


def test_figura_boca_e_cache():
    p = Personagem()
    a = fr.renderizar(p, 200)
    assert fr.renderizar(p, 200) is a
    assert fr.renderizar(p, 200, boca="aberta").tobytes() != a.tobytes()
    with pytest.raises(ValueError):
        fr.renderizar(p, 200, boca="x")


def test_crianca_menor_que_adulto():
    alt = lambda i: 300 - fr.renderizar(Personagem(idade=i), 300).getbbox()[1]  # noqa: E731
    assert alt("crianca") < alt("adolescente") < alt("adulto")


@pytest.mark.parametrize("nome", listar_fallbacks())
def test_quadro_ranking(nome):
    r = Ranking.carregar(config.RANKINGS / f"{nome}.json")
    palco = lr.Palco(r)
    img = lr.quadro(r, 0, palco=palco)
    assert img.size == (config.LARGURA, config.ALTURA) and img.mode == "RGB"
    for pos in palco.posicoes:  # every tag stays inside the stage band, below the title
        assert pos.topo_cabeca - 130 > lr.PALCO_Y0 - 40
        assert pos.chao <= lr.CHAO_Y


def test_palco_escala():
    r = Ranking.carregar(config.RANKINGS / "crises.json")
    p2 = lr.Palco(r, escala=1.5)
    img = p2.desenhar(1)
    assert img.size == (round(config.LARGURA * 1.5), round((lr.PALCO_Y1 - lr.PALCO_Y0) * 1.5))
