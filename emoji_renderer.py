"""Color emoji stickers (flat style) rendered with a local emoji font, no downloads.

Font: assets/fonts/emoji.ttf if present (e.g. Noto Color Emoji, OFL), else Windows' Segoe UI Emoji.
A sticker is the emoji on a white disc with a dark outline and a soft shadow, like the reference style.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

TRACO = (38, 40, 50, 255)
ANEL = (255, 214, 10)  # same yellow as the item label
_FONTES = (config.FONTES / "emoji.ttf", Path("C:/Windows/Fonts/seguiemj.ttf"),
           Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"))
_BASE = 256  # glyph render size (Noto CBDT only renders at 109; Segoe/COLR scales freely)


@lru_cache(maxsize=1)
def _fonte() -> ImageFont.FreeTypeFont | None:
    for c in _FONTES:
        if c.exists():
            try:
                return ImageFont.truetype(str(c), 109 if "Noto" in c.name else _BASE)
            except OSError:
                continue
    return None


def disponivel() -> bool:
    return _fonte() is not None


@lru_cache(maxsize=256)
def glifo(emoji: str) -> Image.Image | None:
    """Tight RGBA crop of the emoji glyph, or None when the font lacks it (tofu)."""
    f = _fonte()
    if f is None:
        return None
    tam = f.size * 2
    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((tam / 2, tam / 2), emoji, font=f, embedded_color=True, anchor="mm")
    caixa = img.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    if caixa is None:
        return None
    img = img.crop(caixa)
    if "‍" in emoji or any(0x1F1E6 <= ord(c) <= 0x1F1FF or 0x1F3FB <= ord(c) <= 0x1F3FF for c in emoji):
        return None  # ZWJ sequences, flags and skin tones may draw as several glyphs
    # tofu / missing glyph: monochrome box without color
    cores = img.convert("RGB").getcolors(maxcolors=4096)
    if cores is not None and len(cores) < 6:
        return None
    return img


def suportado(emoji: str) -> bool:
    return glifo(emoji) is not None


@lru_cache(maxsize=256)
def adesivo(emoji: str, tamanho: int) -> Image.Image | None:
    """Emoji on a white outlined disc with a soft shadow, `tamanho` px wide (shadow adds a margin)."""
    g = glifo(emoji)
    if g is None:
        return None
    ss = 2
    t = tamanho * ss
    m = round(t * 0.12)
    img = Image.new("RGBA", (t + 2 * m, t + 2 * m), (0, 0, 0, 0))
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse([m + t * 0.04, m + t * 0.07, m + t * 1.04, m + t * 1.07], fill=(20, 20, 30, 70))
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(t * 0.03)))
    d = ImageDraw.Draw(img)
    d.ellipse([m, m, m + t, m + t], fill=(255, 255, 255, 255), outline=TRACO, width=max(2, round(t * 0.035)))
    anel = round(t * 0.045)  # colored inner ring, so pale emojis still pop on white
    d.ellipse([m + anel * 1.2, m + anel * 1.2, m + t - anel * 1.2, m + t - anel * 1.2], outline=ANEL + (255,),
              width=anel)
    lado = round(t * 0.74)
    k = lado / max(g.width, g.height)  # scale up or down to fit the disc
    g2 = g.resize((max(1, round(g.width * k)), max(1, round(g.height * k))), Image.Resampling.LANCZOS)
    img.alpha_composite(g2, (m + (t - g2.width) // 2, m + (t - g2.height) // 2))
    return img.resize((img.width // ss, img.height // ss), Image.Resampling.LANCZOS)
