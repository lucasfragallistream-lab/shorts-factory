import pytest
from pydantic import ValidationError

import config
from schemas import Item, Personagem, Ranking, contar_palavras, listar_fallbacks


def _ranking(**extra):
    base = {
        "titulo": "AS 3 COISAS",
        "abertura": "Vamos ver três coisas.",
        "itens": [{"rotulo": f"Item {i}", "narracao": f"Esta é a coisa número {i}."} for i in range(1, 4)],
        "fechamento": "Comenta aí.",
    }
    base.update(extra)
    return base


def test_ranking_valido_e_padroes():
    r = Ranking.model_validate(_ranking())
    assert r.layout == "escada"
    assert r.itens[0].personagem == Personagem()
    segs = r.segmentos()
    assert [s.tipo for s in segs] == ["abertura", "item", "item", "item", "fechamento"]
    assert [s.item for s in segs] == [None, 0, 1, 2, None]
    assert segs[1].rotulo == "Item 1"
    assert r.palavras == sum(contar_palavras(s.texto) for s in segs)
    assert r.duracao_fala_estimada() > 0


@pytest.mark.parametrize("n", [2, 6])
def test_numero_de_itens(n):
    itens = [{"rotulo": "x", "narracao": "texto"}] * n
    with pytest.raises(ValidationError):
        Ranking.model_validate(_ranking(itens=itens))


@pytest.mark.parametrize("campo,valor", [("layout", "pizza"), ("titulo", ""), ("abertura", "!!!"), ("autor", "x")])
def test_ranking_invalido(campo, valor):
    with pytest.raises(ValidationError):
        Ranking.model_validate(_ranking(**{campo: valor}))


@pytest.mark.parametrize("campo,valor", [
    ("idade", "bebe"), ("pele", "verde"), ("cabelo", "moicano"), ("cor_roupa", "dourado"),
    ("expressao", "bravo"), ("acessorios", ["capa"]), ("acessorios", ["oculos", "oculos"]),
    ("acessorios", ["oculos", "barba", "caneca", "fone"]),
])
def test_personagem_invalido(campo, valor):
    with pytest.raises(ValidationError):
        Personagem.model_validate({campo: valor})


def test_personagem_vocabulario_igual_ao_config():
    campos = Personagem.model_fields
    for campo, vocab in (("idade", config.IDADES), ("pele", config.PELES), ("cabelo", config.CABELOS),
                         ("cor_cabelo", config.CORES_CABELO), ("roupa", config.ROUPAS),
                         ("cor_roupa", config.CORES), ("expressao", config.EXPRESSOES)):
        assert set(campos[campo].annotation.__args__) == set(vocab), campo


def test_item_limpa_espacos():
    it = Item(rotulo="  13   anos ", narracao="  muito   espaço  ")
    assert it.rotulo == "13 anos" and it.narracao == "muito espaço"


def test_contar_palavras():
    assert contar_palavras("micro-ondas, às três da manhã!") == 5


def test_listar_fallbacks():
    assert {"crises", "salario"} <= set(listar_fallbacks())
