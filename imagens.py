"""Real photos for ranking items from Wikimedia Commons, only with licenses that allow commercial use.

`buscar(termo)` searches Commons (no API key), keeps the first bitmap whose license is public domain,
CC0, CC BY or CC BY-SA (in that order of preference; NC/ND and unknown licenses are skipped), downloads a
~1000 px rendition into cache/imagens/ and returns the image plus its credit line. Results are cached, so
a ranking only hits the network once. `creditos(...)` writes the lines to paste in the video description.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

import config

API = "https://commons.wikimedia.org/w/api.php"
AGENTE = "shorts-factory/0.1 (local video tool; python urllib)"  # Wikimedia asks for a descriptive agent
CACHE = config.CACHE / "imagens"
LARGURA = 1000
# preference order; anything else (NC, ND, GFDL-only, fair use, unknown) is rejected
LICENCAS = (("pd", r"public domain|^pd\b|pdm"), ("cc0", r"cc0"), ("cc-by", r"^cc[ -]by(?![ -](sa|nc|nd))"),
            ("cc-by-sa", r"^cc[ -]by[ -]sa"))
PROIBIDAS = re.compile(r"\bnc\b|\bnd\b|non-?commercial|no ?deriv|fair use", re.I)


class ErroImagem(RuntimeError):
    pass


@dataclass
class Foto:
    termo: str
    arquivo: Path
    titulo: str
    autor: str
    licenca: str
    url_pagina: str

    @property
    def credito(self) -> str:
        return f"{self.titulo} — {self.autor} — {self.licenca} — {self.url_pagina}"


def _limpar_html(txt: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", txt or "")).strip()


def classificar_licenca(nome: str) -> str | None:
    """Short license class ('pd', 'cc0', 'cc-by', 'cc-by-sa') or None when not allowed."""
    n = (nome or "").strip().lower()
    if not n or PROIBIDAS.search(n):
        return None
    for classe, padrao in LICENCAS:
        if re.search(padrao, n):
            return classe
    return None


def _get(params: dict) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - fixed Wikimedia host
        return json.loads(r.read())


def _candidatos(termo: str) -> list[dict]:
    dados = _get({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                  "gsrsearch": f"filetype:bitmap {termo}", "gsrlimit": 15, "prop": "imageinfo",
                  "iiprop": "url|extmetadata|size|mime", "iiurlwidth": LARGURA})
    paginas = sorted((dados.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    out = []
    for p in paginas:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        nome_lic = _limpar_html((meta.get("LicenseShortName") or {}).get("value", ""))
        classe = classificar_licenca(nome_lic)
        if classe is None or info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        if min(info.get("width", 0), info.get("height", 0)) < 400:
            continue
        out.append({"classe": classe, "licenca": nome_lic, "url": info.get("thumburl") or info.get("url"),
                    "pagina": info.get("descriptionurl", ""), "titulo": p.get("title", "").removeprefix("File:"),
                    "autor": _limpar_html((meta.get("Artist") or {}).get("value", "")) or "autor desconhecido"})
    ordem = {c: i for i, (c, _) in enumerate(LICENCAS)}
    # keep search relevance, but within the first results prefer the most permissive license
    return sorted(out[:6], key=lambda c: ordem[c["classe"]]) + out[6:]


def buscar(termo: str) -> Foto:
    """Search `termo`; if nothing usable, retry dropping the last word ("Almas caviar tin" -> "Almas caviar")."""
    palavras = termo.split()
    erro = None
    for n in range(len(palavras), 0, -1):
        try:
            return _buscar(" ".join(palavras[:n]), termo)
        except ErroImagem as exc:
            erro = exc
    raise erro or ErroImagem(f"termo vazio: '{termo}'")


def _buscar(termo: str, original: str) -> Foto:
    CACHE.mkdir(parents=True, exist_ok=True)
    chave = hashlib.sha256(termo.strip().lower().encode()).hexdigest()[:16]
    meta_arq, img_arq = CACHE / f"{chave}.json", CACHE / f"{chave}.jpg"
    if meta_arq.exists() and img_arq.exists():
        m = json.loads(meta_arq.read_text(encoding="utf-8"))
        return Foto(original, img_arq, m["titulo"], m["autor"], m["licenca"], m["pagina"])
    try:
        cands = _candidatos(termo)
    except Exception as exc:  # noqa: BLE001 - network
        raise ErroImagem(f"busca no Wikimedia falhou para '{termo}': {exc}") from exc
    for c in cands:
        try:
            req = urllib.request.Request(c["url"], headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - Wikimedia upload host
                dados = r.read()
            tmp = CACHE / f"{chave}.tmp"
            tmp.write_bytes(dados)
            Image.open(tmp).convert("RGB").save(img_arq, quality=92)
            tmp.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - try the next candidate
            continue
        meta_arq.write_text(json.dumps({k: c[k] for k in ("titulo", "autor", "licenca", "pagina")},
                                       ensure_ascii=False), encoding="utf-8")
        return Foto(original, img_arq, c["titulo"], c["autor"], c["licenca"], c["pagina"])
    raise ErroImagem(f"nenhuma imagem com licença comercial encontrada para '{termo}'")


def creditos(fotos: list[Foto], destino: Path) -> Path:
    linhas = ["Imagens (Wikimedia Commons):"] + [f"- {f.credito}" for f in fotos]
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino
