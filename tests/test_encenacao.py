import pytest

import encenacao as en
import figure_renderer as fr
from novela_schema import Episodio
from schemas import Personagem

EXPR = {"neutra": "feliz", "deboche": "feliz", "esperanca": "feliz", "triste": "triste", "chorando": "triste",
        "raiva": "raiva", "choque": "chocado", "medo": "preocupado"}
OUV = {"protagonista": "preocupado", "vilao": "raiva", "vila": "feliz", "aliado": "feliz", "misterio": "feliz"}
PAPEIS = {"mae": "protagonista", "filho": "vilao"}


def _fala(quem, a, b, emocao="neutra", **kw):
    return {"quem": quem, "inicio": a, "fim": b, "emocao": emocao,
            "palavras": [{"texto": "x", "inicio": a + 0.1, "fim": a + 0.4}], **kw}


def _encenar(falas):
    return en.encenar(falas, ["mae", "filho"], [220.0, 860.0], PAPEIS, "mae", EXPR, OUV)


def test_raiva_aponta_e_mae_reage():
    at = _encenar([_fala("filho", 1.0, 2.0, "raiva", alvo="mae")])
    ev = en.estados(at["filho"], at, 5.0)
    assert any(pk == "aponta_e" for _, _, _, pk in ev)  # mother is on the left -> mirrored
    mae = en.estados(at["mae"], at, 5.0)
    assert any(e == "chocado" and pk == "mao_peito" for _, e, _, pk in mae)


def test_empurra_move_os_dois():
    at = _encenar([_fala("filho", 1.0, 2.0, "raiva", acao="empurra", alvo="mae")])
    assert at["filho"].x(3.0) < 860 - 300
    assert at["mae"].x(3.0) < 220  # staggered back (clamped to the frame)


def test_abraco_aproxima():
    at = _encenar([_fala("mae", 1.0, 2.0, "esperanca", acao="abraca", alvo="filho")])
    assert abs(at["mae"].x(3.0) - at["filho"].x(3.0)) == pytest.approx(230, abs=1)
    assert any(pk == "abraca" for *_, pk in en.estados(at["filho"], at, 5.0))


def test_entra_e_sai():
    at = _encenar([_fala("filho", 2.0, 3.0, acao="entra"), _fala("filho", 4.0, 5.0, acao="sai")])
    assert at["filho"].x(0.0) > 1080 and at["filho"].x(3.0) == 860 and at["filho"].x(7.0) > 1080


def test_fala_longa_troca_de_gesto():
    at = _encenar([_fala("filho", 1.0, 5.0, "raiva")])
    poses = {pk.removesuffix("_e") for *_, pk in en.estados(at["filho"], at, 6.0)}
    assert {"aponta", "bracos_cima", "parado"} <= poses


def test_poses_renderizam_com_margem():
    p = Personagem(idade="adulto", sexo="masculino", pele="clara", cabelo="curto", cor_cabelo="preto",
                   roupa="camiseta", cor_roupa="azul")
    for pose in fr.POSES:
        img = fr.renderizar(p, 300, "raiva", pose=pose, margem=fr.MARGEM_POSE)
        assert img.width == round((fr.LARG_U + 2 * fr.MARGEM_POSE) * 300 / fr.ALT_U)
    with pytest.raises(ValueError):
        fr.renderizar(p, 300, pose="danca")


def test_schema_valida_alvo():
    base = {"serie": "s", "numero": 1, "titulo": "t", "pergunta": "p",
            "elenco": [{"id": "a", "nome": "A", "papel": "protagonista", "personagem": {}},
                       {"id": "b", "nome": "B", "papel": "vilao", "personagem": {}}],
            "cenas": [{"cenario": "sala", "presentes": ["a", "b"],
                       "falas": [{"quem": "b", "texto": "oi", "acao": "empurra", "alvo": "a"}]}]}
    Episodio.model_validate(base)
    base["cenas"][0]["falas"][0]["alvo"] = None
    with pytest.raises(ValueError):
        Episodio.model_validate(base)


def test_volta_ao_parado_com_tempos_quebrados():
    at = _encenar([_fala("filho", 1.00004, 2.00006, "raiva", acao="empurra", alvo="mae")])
    assert en.estados(at["filho"], at, 9.0)[-1][3] == "parado"
