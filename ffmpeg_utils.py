"""Locate FFmpeg/ffprobe and run them with errors logged to file."""
from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import config


class FFmpegError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def find_ffmpeg() -> str:
    """Return an FFmpeg executable: PATH first, then imageio-ffmpeg."""
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - depends on environment
        raise FFmpegError("FFmpeg não encontrado no PATH nem via imageio-ffmpeg") from exc


@lru_cache(maxsize=1)
def find_ffprobe() -> str | None:
    """Return ffprobe if available (imageio-ffmpeg does not ship it)."""
    caminho = shutil.which("ffprobe")
    if caminho:
        return caminho
    vizinho = Path(find_ffmpeg()).with_name("ffprobe" + Path(find_ffmpeg()).suffix)
    return str(vizinho) if vizinho.exists() else None


def run_ffmpeg(args: list[str], log_path: Path | None = None, **kwargs) -> subprocess.CompletedProcess:
    """Run FFmpeg quietly. stderr goes to the log; failure raises FFmpegError."""
    log_path = Path(log_path or config.FFMPEG_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [find_ffmpeg(), "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.run(cmd, capture_output=True, **kwargs)
    stderr = proc.stderr.decode("utf-8", "replace") if isinstance(proc.stderr, bytes) else (proc.stderr or "")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n")
        if stderr:
            fh.write(stderr + "\n")
    if proc.returncode != 0:
        ultima = stderr.strip().splitlines()[-1] if stderr.strip() else f"código {proc.returncode}"
        raise FFmpegError(f"FFmpeg falhou: {ultima} (log: {log_path})")
    return proc


@lru_cache(maxsize=1)
def listar_encoders() -> frozenset[str]:
    proc = subprocess.run([find_ffmpeg(), "-hide_banner", "-encoders"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    nomes = set()
    for linha in proc.stdout.splitlines():
        partes = linha.split()
        if len(partes) >= 2 and len(partes[0]) == 6 and partes[0][0] in "VAS":
            nomes.add(partes[1])
    return frozenset(nomes)


def tem_encoder(nome: str) -> bool:
    return nome in listar_encoders()


def duracao_midia(caminho: Path) -> float:
    """Duration in seconds: ffprobe when available, else the WAV header."""
    probe = find_ffprobe()
    if probe:
        proc = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                               str(caminho)], capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return float(proc.stdout.strip())
    import wave

    with wave.open(str(caminho), "rb") as w:
        return w.getnframes() / w.getframerate()
