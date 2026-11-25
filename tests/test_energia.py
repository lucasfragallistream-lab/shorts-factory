import json

from PIL import Image

import config
import imagens
import script_generator as sg
from montagem import GANCHO_ROSTO, Montagem
from schemas import Ranking


def _crises(**extra) -> Ranking:
    d = json.loads((config.RANKINGS / "crises.json").read_text(encoding="utf-8"))
    d.update(extra)
    return Ranking.model_validate(d)


def test_licencas_comerciais():
    assert imagens.classificar_licenca("Public domain") == "pd"
    assert imagens.classificar_licenca("CC0") == "cc0"
    assert imagens.classificar_licenca("CC BY 4.0") == "cc-by"
    assert imagens.classificar_licenca("CC BY-SA 3.0") == "cc-by-sa"
    for proibida in ("CC BY-NC 2.0", "CC BY-ND 4.0", "CC BY-NC-SA 4.0", "Fair use", "", "GFDL"):
        assert imagens.classificar_licenca(proibida) is None, proibida


def test_palavra_chave_valida():
    assert _crises(palavra_chave="Degrau").palavra_chave == "Degrau"
    try:
        _crises(palavra_chave="duas palavras")
        raise AssertionError("aceitou duas palavras")
    except ValueError:
        pass


def test_verificar_exige_palavra_no_fechamento():
    r = _crises(palavra_chave="Girafa")
    assert any("palavra_chave" in p for p in sg.verificar(r, palavras=False))


def test_primeiro_quadro_close_e_cartoes(timeline_mock, tmp_path):
    _, tl = timeline_mock
    foto = tmp_path / "f.jpg"
    Image.new("RGB", (800, 600), (200, 80, 40)).save(foto)
    r = _crises(palavra_chave="Degrau")
    m = Montagem(r, tl, fotos={0: foto})
    q0 = m.quadro(0)
    assert q0.size == (config.LARGURA, config.ALTURA)
    assert q0.getpixel((540, 1180)) != q0.getpixel((5, 1900))  # face fills the middle, not a blank frame
    assert m.quadro(int(GANCHO_ROSTO * m.fps) + 2).size == (config.LARGURA, config.ALTURA)
    ini = m.inicio_item[0]
    com_foto = m.quadro(int((ini + 1.2) * m.fps))
    assert com_foto.getpixel((540, 730))[0] > 150  # reddish test photo visible in the middle
    assert m.quadro(int((m.fechamento + 0.8) * m.fps)).size == (config.LARGURA, config.ALTURA)
    tipos = [e.tipo for e in m.eventos_sonoros()]
    assert tipos.count("ding") >= 2  # cta + keyword card
