import camera


def _f(a, b, **kw):
    return {"inicio": a, "fim": b, "emocao": kw.pop("emocao", "neutra"), "destaque": kw.pop("destaque", None), **kw}


def _enq(f):
    return {"cx": f.get("cx", 540), "cy": 900, "z": f.get("z", 1.5)}


def test_desliza_entre_falas_e_nunca_congela():
    falas = [_f(0.2, 2.0, cx=300), _f(2.3, 4.0, cx=780), _f(4.3, 6.0, cx=300, destaque="X")]
    p = camera.planejar(falas, _enq, [], 7.0)
    glides = [c for c in p["cam"] if c[5] == camera.EASE]
    assert len(glides) == 2 and all(camera.GLIDE_MIN <= c[1] <= camera.GLIDE_MAX for c in glides)
    assert camera.parado_max(p["cam"], 7.0) < 4 / 30
    assert p["kick"] and p["kick"][0][0] > 4.3


def test_salto_grande_vira_corte():
    falas = [_f(0.2, 2.0, z=1.0), _f(2.3, 4.0, cx=900, z=2.35)]
    p = camera.planejar(falas, _enq, [], 5.0)
    assert any(c[1] == 0 and c[0] > 2 for c in p["cam"])


def test_segue_quem_anda_e_inclina_na_raiva():
    falas = [_f(0.2, 3.0, emocao="raiva")]
    p = camera.planejar(falas, _enq, [(1.0, 2.0, lambda t: {"cx": 200 + 400 * (t - 1), "cy": 900, "z": 1.25})], 4.0)
    dentro = [c for c in p["cam"] if 1.0 <= c[0] < 2.0]
    assert len(dentro) >= 5 and dentro[0][2] != dentro[-1][2]  # x changes while following
    assert p["roll"][0][1] != 0 and p["roll"][0][2] > 1


def test_pos_nunca_mostra_fora_do_palco():
    x, y, s = camera.pos(0, 0, 1.5)
    assert x <= 0 and y <= 0 and x >= 1080 - 1080 * s and y >= 1920 - 1920 * s
