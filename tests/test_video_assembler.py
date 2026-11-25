import re
import subprocess
from pathlib import Path

import pytest
from PIL import Image

import bgm
import config
import ffmpeg_utils
import video_assembler as va


def _lufs(caminho):
    proc = subprocess.run([ffmpeg_utils.find_ffmpeg(), "-hide_banner", "-nostats", "-i", str(caminho), "-af",
                           "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", proc.stderr)[-1])


@pytest.mark.parametrize("com_bgm", [True, False])
def test_mix_normalizado(timeline_mock, tmp_path, com_bgm):
    _, tl = timeline_mock
    trilha = bgm.gerar("leve", tmp_path / "b.wav", duracao=20.0) if com_bgm else None
    saida = va.mixar_audio(Path(tl["audio"]), tmp_path / "mix.wav", tl["duracao"], trilha)
    assert ffmpeg_utils.duracao_midia(saida) == pytest.approx(tl["duracao"], abs=0.01)
    assert _lufs(saida) == pytest.approx(va.LUFS_ALVO, abs=0.3)


def test_encoder_auto():
    assert va.escolher_encoder("auto") in ("h264_nvenc", "libx264")
    assert va.escolher_encoder("libx264") == "libx264"


def test_codificar_quadros_sinteticos(timeline_mock, tmp_path):
    _, tl = timeline_mock
    audio = va.mixar_audio(Path(tl["audio"]), tmp_path / "mix.wav", tl["duracao"], None)

    def quadro(i):
        return Image.new("RGB", (config.LARGURA, config.ALTURA), (i * 8 % 256, 120, 200))

    r = va.codificar(quadro, 30, audio, tmp_path / "p.mp4", encoder="libx264")
    info = va.conferir_video(r.mp4)
    assert (info["largura"], info["altura"]) == (1080, 1920)
    assert info["fps"] == pytest.approx(30)
    assert info["duracao"] == pytest.approx(1.0, abs=0.05)


def test_codificar_rejeita_quadro_errado(timeline_mock, tmp_path):
    _, tl = timeline_mock
    with pytest.raises(va.ErroMontagem):
        va.codificar(lambda i: Image.new("RGB", (10, 10)), 3, Path(tl["audio"]), tmp_path / "x.mp4",
                     encoder="libx264")
