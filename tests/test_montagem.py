import config
import layout_renderer as lr
from montagem import Montagem
from schemas import Ranking


def _montagem(timeline_mock, sem_visuais: bool = False):
    _, tl = timeline_mock
    if sem_visuais:
        tl = dict(tl, segmentos=[dict(s, visuais=[]) for s in tl["segmentos"]])
    return Montagem(Ranking.carregar(config.RANKINGS / "crises.json"), tl)


def test_quadros_formato(timeline_mock):
    m = _montagem(timeline_mock)
    for f, _ in m.quadros_chave():
        img = m.quadro(f)
        assert img.size == (config.LARGURA, config.ALTURA) and img.mode == "RGB"
    assert m.quadro(m.n_frames - 1).size == (config.LARGURA, config.ALTURA)  # closing frame (item_atual == n)


def test_camera_largo_e_item(timeline_mock):
    m = _montagem(timeline_mock, sem_visuais=True)
    assert m.camera(2.0).z == 1.0  # after the opening pull-out
    ini = m.inicio_item[1]
    cam = m.camera(ini + 1.0)
    assert cam.z > 1.2
    pos = m.palco1.posicoes[1]
    assert abs(cam.cx - (pos.caixa[0] + pos.caixa[2]) / 2) < 1
    assert m.camera(m.fechamento + 2.0).z < 1.1  # wide shot with a slow push


def test_revelacao_progressiva(timeline_mock):
    m = _montagem(timeline_mock)
    assert not m._revelado(3, 1.0)
    assert m._revelado(0, m.inicio_item[0] + 0.1)
    assert all(m._revelado(i, m.fechamento) for i in range(4))


def test_eventos_por_palavra_e_cta(timeline_mock):
    _, tl = timeline_mock
    tl = dict(tl, segmentos=[dict(s, visuais=[]) for s in tl["segmentos"]])
    item0 = next(s for s in tl["segmentos"] if s["tipo"] == "item" and s["item"] == 0)
    palavra = next(w["texto"] for w in item0["palavras"][3:] if len(w["texto"]) >= 5)
    item0["visuais"] = [{"palavra": palavra, "emoji": "🏠"}]
    m = Montagem(Ranking.carregar(config.RANKINGS / "crises.json"), tl)
    ev = [e for e in m.eventos if e.emoji == "🏠"]
    assert len(ev) == 1 and item0["inicio"] < ev[0].inicio < item0["fim"]
    # the camera punches in on the face while the emoji is on screen
    assert m.camera(ev[0].inicio + 0.5).z > m.camera(ev[0].inicio - 0.6).z
    assert m.quadro(int((ev[0].inicio + 0.5) * m.fps)).size == (config.LARGURA, config.ALTURA)
    # items without visuals still get a camera beat
    assert any(e.item == 1 and e.emoji == "" for e in m.eventos)
    # the CTA segment exists in the timeline and shows the card frame without errors
    if m.cta:
        assert m.quadro(int((m.cta[0] + 1.0) * m.fps)).size == (config.LARGURA, config.ALTURA)


def test_adesivo_parado_durante_o_zoom(timeline_mock):
    """Regression (20/11/2026): the emoji slid ~50 px/frame and flipped sides during the punch-in."""
    m = _montagem(timeline_mock)
    for e in [e for e in m.eventos if e.emoji and e.item is not None]:
        lugares = set()
        for f in range(int(e.inicio * m.fps) + 1, int(e.fim * m.fps)):
            m._recortar(m.palco.fundo, m.camera(f / m.fps))  # camera moves, sticker spot must not
            lugares.add(m._lugar_adesivo(e))
        assert len(lugares) == 1


def test_gancho_abre_no_ultimo_item(timeline_mock):
    m = _montagem(timeline_mock)
    assert m.camera(0.0).z > 1.4 and m.camera(2.0).z < 1.1


def test_rotulo_e_legenda_na_zona_segura():
    assert lr.LEGENDA_Y + 84 < config.ALTURA - 380 + 60  # two-line caption clamps at Y_MAX
    assert lr.CHAO_Y < lr.ROTULO_Y < lr.LEGENDA_Y
