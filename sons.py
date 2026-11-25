"""Real sound effects from Wikimedia Commons, public domain / CC0 only (no attribution chains, safe to monetize).

`candidatos(termo)` lists audio files with an allowed license; `baixar(titulo)` downloads one and converts it to
mono 48 kHz WAV in cache/sons/. `creditos()` writes what was used. Same agent/license rules as imagens.py.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path

import config
import imagens
from ffmpeg_utils import find_ffmpeg

CACHE = config.CACHE / "sons"
PERMITIDAS = ("pd", "cc0")


def candidatos(termo: str, limite: int = 20, dur_max: float = 90.0) -> list[dict]:
    dados = imagens._get({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                          "gsrsearch": f"filetype:audio {termo}", "gsrlimit": limite, "prop": "imageinfo|videoinfo",
                          "iiprop": "url|extmetadata|mime|size", "viprop": "url|extmetadata|mime|size"})
    out = []
    for p in sorted((dados.get("query") or {}).get("pages", {}).values(), key=lambda q: q.get("index", 99)):
        info = (p.get("videoinfo") or p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = imagens._limpar_html((meta.get("LicenseShortName") or {}).get("value", ""))
        classe = imagens.classificar_licenca(lic)
        dur = float(info.get("duration") or 0)
        if classe not in PERMITIDAS or (dur and dur > dur_max):
            continue
        out.append({"titulo": p.get("title", "").removeprefix("File:"), "url": info.get("url"), "licenca": lic,
                    "dur": round(dur, 1), "pagina": info.get("descriptionurl", ""),
                    "autor": imagens._limpar_html((meta.get("Artist") or {}).get("value", "")) or "autor desconhecido"})
    return out


def baixar(c: dict) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    nome = re.sub(r"[^a-z0-9]+", "_", c["titulo"].lower()).strip("_")[:60]
    wav = CACHE / f"{nome}.wav"
    if wav.exists():
        return wav
    bruto = CACHE / f"{nome}.orig"
    req = urllib.request.Request(c["url"], headers={"User-Agent": imagens.AGENTE})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed Wikimedia host
        bruto.write_bytes(r.read())
    subprocess.run([find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(bruto), "-ac", "1",
                    "-ar", "48000", str(wav)], check=True)
    bruto.unlink(missing_ok=True)
    (CACHE / f"{nome}.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return wav


def creditos(usados: list[dict], destino: Path) -> Path:
    linhas = [f"{c['titulo']} — {c['autor']} — {c['licenca']} — {c['pagina']}" for c in usados]
    destino.write_text("Sons (Wikimedia Commons, domínio público / CC0):\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    return destino
