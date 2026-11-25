"""Animates one of our flat frames with Wan 2.2 TI2V-5B (Apache-2.0, local GPU). Runs in .venv-video.

Usage: .venv-video/Scripts/python.exe tools/wan_clipe.py IMAGEM PROMPT SAIDA.mp4 [--frames 81] [--passos 30]
The model lives in modelos/wan22_ti2v_5b (Hugging Face Wan-AI/Wan2.2-TI2V-5B-Diffusers).
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODELO = RAIZ / "modelos" / "wan22_ti2v_5b"
NEGATIVO = ("photorealistic, 3d render, realistic skin, texture, blurry, low quality, distorted face, extra limbs, "
            "deformed hands, morphing, flicker, watermark, text, subtitles, static image")
ESTILO = ("Flat 2D vector cartoon animation, clean thick dark outlines, solid flat colors, simple shapes, "
          "same characters and colors as the first frame. ")


def main(argv=None) -> int:
    import torch
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
    from diffusers.utils import export_to_video
    from PIL import Image

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("imagem")
    ap.add_argument("prompt")
    ap.add_argument("saida")
    ap.add_argument("--frames", type=int, default=81)  # 4k+1
    ap.add_argument("--passos", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    img = Image.open(a.imagem).convert("RGB")
    w, h = img.size
    t0 = time.time()
    vae = AutoencoderKLWan.from_pretrained(MODELO, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(MODELO, vae=vae, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    print(f"carregado em {time.time() - t0:.0f} s", flush=True)
    t1 = time.time()
    quadros = pipe(image=img, prompt=ESTILO + a.prompt, negative_prompt=NEGATIVO, height=h, width=w,
                   num_frames=a.frames, num_inference_steps=a.passos, guidance_scale=5.0,
                   generator=torch.Generator("cpu").manual_seed(a.seed)).frames[0]
    export_to_video(quadros, a.saida, fps=24)
    print(f"gerado em {time.time() - t1:.0f} s -> {a.saida}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
