from pathlib import Path

import pytest

import ffmpeg_utils


def test_find_ffmpeg():
    assert Path(ffmpeg_utils.find_ffmpeg()).exists()


def test_run_ffmpeg_ok(tmp_path):
    saida = tmp_path / "x.wav"
    log = tmp_path / "ff.log"
    ffmpeg_utils.run_ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.1", str(saida)], log)
    assert saida.stat().st_size > 0
    assert log.read_text(encoding="utf-8").startswith("$ ")


def test_run_ffmpeg_erro(tmp_path):
    with pytest.raises(ffmpeg_utils.FFmpegError):
        ffmpeg_utils.run_ffmpeg(["-i", str(tmp_path / "nao_existe.mp4"), "-f", "null", "-"], tmp_path / "ff.log")


def test_encoders():
    assert ffmpeg_utils.tem_encoder("libx264")
    assert not ffmpeg_utils.tem_encoder("encoder_inexistente")
