import voice_engine as ve
from tools.tts_worker import _mapear


def test_mapear_texto_igual():
    w = [("Aos", 0.0, 0.2), ("treze", 0.25, 0.5), ("anos.", 0.55, 0.9)]
    out = _mapear("Aos treze anos.", w)
    assert [p["texto"] for p in out] == ["Aos", "treze", "anos"]
    assert out[1]["inicio"] == 0.25 and out[2]["fim"] == 0.9


def test_mapear_whisper_diferente_mantem_texto_do_roteiro():
    # whisper writes numbers as digits and drops a word; the script words must survive with sane times
    w = [("Aos", 0.0, 0.2), ("13", 0.25, 0.5), ("vem", 0.9, 1.1), ("crise", 1.2, 1.6)]
    out = _mapear("Aos treze anos vem a crise", w)
    assert [p["texto"] for p in out] == ["Aos", "treze", "anos", "vem", "a", "crise"]
    inicios = [p["inicio"] for p in out]
    assert inicios == sorted(inicios) and all(p["fim"] > p["inicio"] for p in out)


def test_motor_chatterbox_registrado():
    assert "chatterbox" in ve.MOTORES
