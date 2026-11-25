"""Generic video plumbing: audio mix/loudness, frame encoding through an FFmpeg pipe, ffprobe check.

The frame source is any callable `gerar_quadro(i) -> PIL.Image (RGB 1080x1920)`. The ranking
layout/camera that produces those frames arrives in phase R4 (the v1 paper-cutout montage lives in
legado/montagem_v1.py).

Audio: voice + BGM at -22 dB with sidechain ducking, normalized to -14 LUFS
(EBU R128 measured, exact gain + -1.5 dB peak limiter).
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image

import config
import ffmpeg_utils

L, A = config.LARGURA, config.ALTURA
LUFS_ALVO = -14.0
PICO_MAX_DB = -1.5


class ErroMontagem(RuntimeError):
    pass


# --- audio -------------------------------------------------------------------
def _medir_lufs(args_entrada: list[str], filtro: str) -> float:
    """First pass: integrated loudness (EBU R128) of the stereo mix, as the final check measures it."""
    cmd = [ffmpeg_utils.find_ffmpeg(), "-hide_banner", "-nostats", *args_entrada, "-filter_complex",
           f"{filtro},aformat=sample_rates=48000:channel_layouts=stereo,ebur128=framelog=quiet[out]",
           "-map", "[out]", "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    achados = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", proc.stderr)
    if proc.returncode != 0 or not achados or achados[-1] == "-inf":
        raise ErroMontagem("falha ao medir a loudness do áudio (1ª passada); o áudio está vazio?")
    return float(achados[-1])


def mixar_audio(voz: Path, saida: Path, duracao: float, bgm: Path | None = None) -> Path:
    """Voice (+ BGM -22 dB ducked by the voice) -> -14 LUFS in two passes (measure, exact gain), 48 kHz stereo."""
    cauda = f"aresample=48000,apad=whole_dur={duracao},atrim=0:{duracao}"
    if bgm is None:
        entrada = ["-i", str(voz)]
        base = "[0:a]anull"
    else:
        base = (
            "[0:a]aformat=sample_rates=48000:channel_layouts=mono,asplit=2[v1][v2];"
            f"[1:a]aformat=sample_rates=48000:channel_layouts=mono,volume=-22dB,"
            f"afade=t=in:d=0.5,afade=t=out:st={max(duracao - 1.5, 0)}:d=1.5[bg];"
            "[bg][v1]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[duck];"
            "[v2][duck]amix=inputs=2:duration=first:normalize=0"
        )
        entrada = ["-i", str(voz), "-stream_loop", "-1", "-i", str(bgm)]
    ganho = LUFS_ALVO - _medir_lufs(entrada, base)  # exact linear gain to the target, then a peak guard
    norm = (f"aformat=sample_rates=48000:channel_layouts=stereo,volume={ganho:.2f}dB,"
            f"alimiter=limit={10 ** (PICO_MAX_DB / 20):.4f}:level=false")
    args = ["-y", *entrada, "-filter_complex", f"{base},{norm},{cauda}[out]",
            "-map", "[out]", "-ac", "2", "-c:a", "pcm_s16le", str(saida)]
    ffmpeg_utils.run_ffmpeg(args)
    return saida


# --- encoding ----------------------------------------------------------------
def escolher_encoder(pedido: str = "auto") -> str:
    if pedido == "auto":
        return "h264_nvenc" if ffmpeg_utils.tem_encoder("h264_nvenc") else "libx264"
    if not ffmpeg_utils.tem_encoder(pedido):
        raise ErroMontagem(f"encoder {pedido} não disponível neste FFmpeg")
    return pedido


def _args_video(encoder: str) -> list[str]:
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0", "-profile:v", "high"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-profile:v", "high"]


@dataclass
class ResultadoVideo:
    mp4: Path
    encoder: str
    frames: int
    segundos_render: float


def codificar(gerar_quadro: Callable[[int], Image.Image], n: int, audio: Path, saida: Path,
              fps: int = config.FPS, encoder: str = "auto", progresso=None) -> ResultadoVideo:
    """Pipe n RGB frames to FFmpeg and mux them with `audio` (cut to n/fps seconds)."""
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    enc = escolher_encoder(encoder)
    log = config.FFMPEG_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_utils.find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L}x{A}", "-r", str(fps), "-i", "-",
           "-i", str(audio), "-map", "0:v", "-map", "1:a", *_args_video(enc),
           "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
           "-t", f"{n / fps:.3f}", "-movflags", "+faststart", str(saida)]
    inicio = time.perf_counter()
    with log.open("a", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n")
        fh.flush()
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=fh)
        try:
            for i in range(n):
                quadro = gerar_quadro(i)
                if quadro.size != (L, A) or quadro.mode != "RGB":
                    raise ErroMontagem(f"quadro {i} inválido: {quadro.mode} {quadro.size}")
                proc.stdin.write(quadro.tobytes())
                if progresso and i % fps == 0:
                    progresso(i, n)
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        except Exception:
            proc.kill()
            proc.wait()
            raise
        code = proc.wait()
    if code != 0:
        raise ErroMontagem(f"FFmpeg falhou ao codificar o vídeo (código {code}); veja {log}")
    return ResultadoVideo(saida, enc, n, time.perf_counter() - inicio)


def conferir_video(mp4: Path) -> dict:
    """ffprobe: width, height, fps and duration of the first video stream and container."""
    probe = ffmpeg_utils.find_ffprobe()
    if not probe:
        raise ErroMontagem("ffprobe não encontrado para conferir o vídeo")
    proc = subprocess.run([probe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height,r_frame_rate,nb_frames,codec_name:format=duration",
                           "-of", "json", str(mp4)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise ErroMontagem(f"ffprobe falhou: {proc.stderr.strip()}")
    info = json.loads(proc.stdout)
    st = info["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return {"largura": st["width"], "altura": st["height"], "fps": float(num) / float(den),
            "duracao": float(info["format"]["duration"]), "frames": int(st.get("nb_frames", 0) or 0),
            "codec": st["codec_name"]}
