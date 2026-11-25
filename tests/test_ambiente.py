"""Phase 0 smoke test: required packages import and a FFmpeg binary is reachable."""
import importlib
import shutil

import pytest

MODULOS = ["PIL", "numpy", "edge_tts", "pydantic", "google.genai", "imageio_ffmpeg"]


@pytest.mark.parametrize("nome", MODULOS)
def test_import(nome):
    importlib.import_module(nome)


def test_ffmpeg_disponivel():
    import imageio_ffmpeg

    assert shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
