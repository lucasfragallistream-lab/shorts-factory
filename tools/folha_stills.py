"""Contact sheet from a folder of stills (frame number on each tile). Usage: python tools/folha_stills.py DIR OUT.jpg [cols]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
d, out = Path(sys.argv[1]), sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 8
fs = sorted(d.glob("f*.png"))
W, H = 240, 427
rows = (len(fs) + cols - 1) // cols
folha = Image.new("RGB", (cols * W, rows * (H + 18)), "black")
dr = ImageDraw.Draw(folha)
for i, f in enumerate(fs):
    x, y = (i % cols) * W, (i // cols) * (H + 18)
    folha.paste(Image.open(f).convert("RGB").resize((W, H)), (x, y + 18))
    dr.text((x + 4, y + 3), f"{int(f.stem[1:]) / 30:.1f}s", fill="white")
folha.save(out, quality=86)
