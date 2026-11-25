import numpy as np
import pytest
from PIL import Image, ImageChops

import captions as cp
import config


def _w(texto, ini, fim):
    return {"texto": texto, "inicio": ini, "fim": fim}


def test_blocos_por_frase_e_equilibrados():
    palavras = ["Chega", "Eu", "vou", "provar", "agora", "mesmo", "para", "todo", "mundo"]
    fala = {"inicio": 0.0, "texto": "Chega. Eu vou provar agora mesmo para todo mundo!",
            "palavras": [_w(t, i * 0.3, i * 0.3 + 0.25) for i, t in enumerate(palavras)]}
    blocos = cp.montar_blocos([fala])
    assert [len(b.palavras) for b in blocos] == [1, 4, 4]
    assert all(b.inicio < b.fim for b in blocos)
    assert all(a.fim <= b.inicio + 1e-9 for a, b in zip(blocos, blocos[1:]))


def test_blocos_sem_pontuacao_usam_pausa():
    ws = [_w("a", 0, .2), _w("b", .25, .4), _w("c", 1.0, 1.2), _w("d", 1.25, 1.4)]
    blocos = cp.montar_blocos([{"inicio": 0, "texto": "x", "palavras": ws}])
    assert [len(b.palavras) for b in blocos] == [2, 2]


def test_blocos_reais_entre_1_e_4(timeline_mock):
    _, tl = timeline_mock
    blocos = cp.montar_blocos(tl["segmentos"])
    assert blocos and all(1 <= len(b.palavras) <= cp.MAX_PALAVRAS for b in blocos)


def test_palavra_ativa():
    b = cp.Bloco([_w("um", 0, .2), _w("dois", .3, .5)], 0, .7)
    assert cp.palavra_ativa(b, 0.1) == 0
    assert cp.palavra_ativa(b, 0.35) == 1
    assert cp.palavra_ativa(b, 0.9) is None


@pytest.mark.parametrize("centro_y", [cp.CENTRO_Y, cp.CENTRO_Y_GERAL])
def test_legenda_na_zona_segura(centro_y):
    base = Image.new("RGB", (config.LARGURA, config.ALTURA), (90, 120, 150))
    img = base.copy()
    b = cp.Bloco([_w("PALAVRA", 0, .3), _w("COMPRIDA", .3, .6), _w("AQUI", .6, .8), _w("TAMBÉM", .8, 1)], 0, 1)
    cp.desenhar_bloco(img, b, 0.31, centro_y)
    caixa = ImageChops.difference(img, base).getbbox()
    assert caixa is not None
    x0, _, x1, y1 = caixa
    assert x0 >= cp.X_MIN and x1 <= cp.X_MAX
    assert y1 <= cp.Y_MAX
    amarelo = np.all(np.asarray(img) == cp.AMARELO, axis=-1).sum()
    assert amarelo > 100  # active word highlighted


def test_gancho_so_nos_primeiros_2s():
    base = Image.new("RGB", (config.LARGURA, config.ALTURA), (0, 0, 0))
    a, b = base.copy(), base.copy()
    cp.desenhar_gancho(a, "TESTE DE GANCHO", 0.5)
    cp.desenhar_gancho(b, "TESTE DE GANCHO", 2.1)
    assert ImageChops.difference(a, base).getbbox() is not None
    assert ImageChops.difference(b, base).getbbox() is None
