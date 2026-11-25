import json
from pathlib import Path

import numpy as np
import pytest

import sons
from tools import maquinista_som as ms

SRC = Path(__file__).resolve().parent.parent / "motion" / "trolley" / "src"
EPISODIOS = sorted(p for p in SRC.glob("ep*") if (p / "eventos.json").exists())
PALAVRAS = [{"w": w, "a": i * 0.5} for i, w in enumerate(["O", "trilho", "A", "a", "trilho", "B.", "A"])]


def test_ancoras_respeitam_maiusculas_e_ocorrencia():
    assert ms.resolver("trilho#2", PALAVRAS) == 2.0
    assert ms.resolver("A", PALAVRAS) == 1.0 and ms.resolver("A#2", PALAVRAS) == 3.0
    assert ms.resolver("B", PALAVRAS) == 2.5  # punctuation stripped
    assert ms.resolver(12.5, PALAVRAS) == 12.5
    assert ms.tempo_de({"at": "A", "off": -0.1}, PALAVRAS) == 0.9
    with pytest.raises(SystemExit):
        ms.resolver("C", PALAVRAS)


def test_som_so_aceita_dominio_publico_ou_cc0():
    assert sons.PERMITIDAS == ("pd", "cc0")


def test_trilho_acelera_cada_junta_chega_mais_rapido():
    juntas = ms._juntas({"v0": 22.0, "a": 0.2, "z_fim": 0.6}, 59.65)
    gaps = np.diff(juntas)
    assert len(juntas) > 150 and np.all(gaps[1:] <= gaps[:-1] + 1e-9)
    assert gaps[0] > gaps[-1] * 1.4  # the clack-clack speeds up with the train


def test_mascara_de_silencio_zera_a_janela():
    m = ms.mascara([(1.0, 2.0)])
    sr = ms.SR
    assert m[int(1.2 * sr):int(1.9 * sr)].max() == 0
    assert m[int(0.5 * sr)] == 1 and m[int(2.5 * sr)] == 1


def test_take_reaproveitado_sincroniza_pela_fala_e_para_antes_do_voo(tmp_path):
    src, takes = tmp_path / "src", tmp_path / "pub" / "takes"
    (src / "epA").mkdir(parents=True)
    takes.mkdir(parents=True)
    (takes / "takes.json").write_text(json.dumps({"epA_freio": {"ep": "epA", "f0": 180, "f1": 390, "de": 6.0, "ate": 13.0}}))
    (src / "epA" / "timeline.json").write_text(json.dumps({"linhas": [{"id": "freio", "texto": "Puxa!", "a": 7.0}]}))
    linhas = [{"id": "freio", "texto": "Puxa!", "a": 9.5}]
    keys = [{"pose": "lever_cu", "t": 9.0, "move": "cut", "take": "epA_freio", "alinha": "freio"},
            {"pose": "cab_mcu", "t": 11.0, "move": "whip", "dur": 0.3, "take": "epA_freio"},
            {"pose": "fork_aerial", "t": 14.0, "move": "fly", "dur": 1.0}]
    ms._ligar_takes(keys, takes / "takes.json", src / "epB", linhas)
    assert keys[0]["delta"] == keys[1]["delta"] == 2.5 and keys[0]["clip_f0"] == 180
    assert keys[1]["clip_ate"] == 13.0  # the clip stops where the 3D fly leaves
    keys[2]["t"] = 17.0  # the fly now leaves at 16 s = 13.5 s of the clip, past its last frame
    with pytest.raises(SystemExit):
        ms._ligar_takes(keys, takes / "takes.json", src / "epB", linhas)


@pytest.mark.skipif(not EPISODIOS, reason="nenhum episódio gerado")
@pytest.mark.parametrize("ep", EPISODIOS, ids=lambda p: p.name)
def test_episodio_gerado_cabe_e_chaves_em_ordem(ep):
    tl = json.loads((ep / "timeline.json").read_text(encoding="utf-8"))
    ev = json.loads((ep / "eventos.json").read_text(encoding="utf-8"))
    assert tl["fala_fim"] <= tl["contagem"] - 0.3  # voice ends before the countdown
    assert 3.3 <= tl["palavras_por_s"] <= 3.9  # kit pacing
    ts = [k["t"] for k in ev["keys"]]
    assert ts == sorted(ts) and ts[0] == 0
    # story cuts: ~1 per video in the kit; train inserts / their way back / the countdown montage are tagged apart
    historia = [k for k in ev["keys"] if k["move"] == "cut" and not k.get("tag") and k["t"] > 0]
    assert len(historia) <= 2
    assert all(b < 61.0 for b in ev["batidas"])
    for a, b in ev.get("silencios", []):
        assert 0.8 <= b - a <= 1.5 and not any(a <= x < b for x in ev["batidas"])  # the drop is total
