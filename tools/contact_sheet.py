"""Contact sheets: many labeled thumbnails in one PNG, for cheap visual review.

Usage: python tools/contact_sheet.py IMAGEM... [--saida output/contact_sheet.png]
Phase-specific sheets (R2, R4) add their own builders here.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from PIL import Image, ImageDraw, ImageOps  # noqa: E402

import config  # noqa: E402
from estilo import fonte as _fonte  # noqa: E402

FUNDO = (38, 38, 44)
FUNDO_THUMB = (232, 226, 214)
TEXTO = (236, 236, 236)


def montar(itens: list[tuple[Image.Image, str]], colunas: int, thumb: tuple[int, int],
           titulo: str | None = None, margem: int = 10, rotulo_px: int = 14) -> Image.Image:
    """Grid of thumbnails (fit inside `thumb`, aspect kept) with a label under each."""
    fonte = _fonte(rotulo_px)
    fonte_titulo = _fonte(rotulo_px + 8)
    tw, th = thumb
    cel_h = th + rotulo_px + 8
    linhas = (len(itens) + colunas - 1) // colunas
    topo = (rotulo_px + 8 + 2 * margem) if titulo else margem
    largura = margem + colunas * (tw + margem)
    altura = topo + linhas * (cel_h + margem)
    folha = Image.new("RGB", (largura, altura), FUNDO)
    d = ImageDraw.Draw(folha)
    if titulo:
        d.text((margem, margem), titulo, fill=TEXTO, font=fonte_titulo)
    for i, (img, rotulo) in enumerate(itens):
        x = margem + (i % colunas) * (tw + margem)
        y = topo + (i // colunas) * (cel_h + margem)
        cel = Image.new("RGBA", (tw, th), FUNDO_THUMB + (255,))
        mini = ImageOps.contain(img.convert("RGBA"), (tw, th), Image.Resampling.LANCZOS)
        cel.alpha_composite(mini, ((tw - mini.width) // 2, (th - mini.height) // 2))
        folha.paste(cel.convert("RGB"), (x, y))
        d.text((x + tw // 2, y + th + 4), rotulo, fill=TEXTO, font=fonte, anchor="ma")
    return folha


def empilhar(folhas: list[Image.Image]) -> Image.Image:
    largura = max(f.width for f in folhas)
    out = Image.new("RGB", (largura, sum(f.height for f in folhas)), FUNDO)
    y = 0
    for f in folhas:
        out.paste(f, ((largura - f.width) // 2, y))
        y += f.height
    return out


def folha_r2(saida: Path) -> Path:
    """R2 review sheet: ages x expressions, accessories/clothes, and assembled ranking frames."""
    import figure_renderer as fr
    import layout_renderer as lr
    from schemas import Personagem, Ranking

    idades = config.IDADES
    exprs = config.EXPRESSOES
    base = dict(pele="media", cabelo="curto", cor_cabelo="castanho", roupa="camiseta", cor_roupa="azul")
    figs = []
    for e in exprs:
        for i in idades:
            p = Personagem(idade=i, expressao=e, **base)
            figs.append((fr.renderizar(p, 420), f"{i} / {e}"))
    figs.append((fr.renderizar(Personagem(**base), 420, boca="aberta"), "boca aberta"))
    figs.append((fr.renderizar(Personagem(**base), 420, piscando=True), "piscando"))
    variados = [
        dict(idade="crianca", sexo="feminino", pele="clara", cabelo="rabo", cor_cabelo="loiro", roupa="vestido",
             cor_roupa="rosa", acessorios=["mochila"]),
        dict(idade="adolescente", pele="negra", cabelo="espetado", roupa="moletom", cor_roupa="verde",
             acessorios=["fone", "celular"]),
        dict(idade="jovem", sexo="feminino", pele="morena", cabelo="comprido", cor_cabelo="preto", roupa="jaqueta",
             cor_roupa="vermelho", acessorios=["bone", "sacola"]),
        dict(idade="adulto", pele="clara", cabelo="liso", cor_cabelo="ruivo", roupa="social", cor_roupa="branco",
             acessorios=["gravata", "caneca", "bigode"]),
        dict(idade="meia_idade", sexo="feminino", pele="media", cabelo="coque", cor_cabelo="grisalho",
             roupa="camisa", cor_roupa="roxo", acessorios=["oculos", "colar"]),
        dict(idade="idoso", pele="negra", cabelo="careca", cor_cabelo="branco", roupa="camisa", cor_roupa="bege",
             acessorios=["oculos", "bengala", "barba"]),
        dict(idade="jovem", pele="media", cabelo="cacheado", cor_cabelo="castanho", roupa="camiseta",
             cor_roupa="amarelo", acessorios=["oculos", "celular"]),
        dict(idade="adulto", sexo="feminino", pele="negra", cabelo="cacheado", cor_cabelo="preto", roupa="vestido",
             cor_roupa="azul_claro", acessorios=["colar", "caneca"]),
    ]
    for v in variados:
        figs.append((fr.renderizar(Personagem(**v), 420), f"{v['idade']} {v['roupa']}"))
    f1 = montar(figs, 8, (170, 300), "Personagens: idades x expressoes, bocas, roupas e acessorios", rotulo_px=12)
    crises = Ranking.carregar(config.RANKINGS / "crises.json")
    palco = lr.Palco(crises)
    quadros = [(lr.quadro(crises, None, palco=palco), "crises: geral"),
               (lr.quadro(crises, 0, palco=palco), "crises: item 1"),
               (lr.quadro(crises, 3, palco=palco), "crises: item 4")]
    for nome, i in (("top5_fobias", 2), ("salario", 1)):
        caminho = config.RANKINGS / f"{nome}.json"
        if caminho.exists():
            r = Ranking.carregar(caminho)
            quadros.append((lr.quadro(r, i), f"{nome}: item {i + 1}"))
    f2 = montar(quadros, len(quadros), (324, 576), "Layout escada montado (1080x1920)")
    saida.parent.mkdir(parents=True, exist_ok=True)
    empilhar([f1, f2]).save(saida, optimize=True)
    return saida


def folha_r4(timeline: Path, ranking: Path, saida: Path) -> Path:
    """R4 review sheet: key frames of the assembled ranking video."""
    import json

    from montagem import Montagem
    from schemas import Ranking

    tl = json.loads(Path(timeline).read_text(encoding="utf-8"))
    r = Ranking.carregar(ranking)
    fotos = {}
    for i, it in enumerate(r.itens):  # real photos (cached by imagens.py; skipped if not found)
        if it.imagem:
            try:
                import imagens
                fotos[i] = imagens.buscar(it.imagem).arquivo
            except Exception:  # noqa: BLE001
                pass
    m = Montagem(r, tl, fotos=fotos)
    itens = [(m.quadro(f), f"{r} ({f / tl['fps']:.1f} s)") for f, r in m.quadros_chave()]
    saida.parent.mkdir(parents=True, exist_ok=True)
    montar(itens, 6, (270, 480), "R4: quadros-chave").save(saida, optimize=True)
    return saida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("imagens", nargs="*", type=Path, help="imagens para a folha")
    ap.add_argument("--r2", action="store_true", help="gera a folha de revisão da fase R2")
    ap.add_argument("--r4", nargs=2, type=Path, metavar=("TIMELINE", "RANKING"),
                    help="quadros-chave do vídeo montado (fase R4)")
    ap.add_argument("--saida", type=Path, default=config.OUTPUT / "contact_sheet.png")
    ap.add_argument("--colunas", type=int, default=6)
    args = ap.parse_args(argv)
    if args.r2:
        print(folha_r2(config.OUTPUT / "contact_sheet_r2.png"))
        return 0
    if args.r4:
        print(folha_r4(args.r4[0], args.r4[1], config.OUTPUT / "contact_sheet_r4.png"))
        return 0
    if not args.imagens:
        ap.error("informe imagens ou --r2")
    itens = [(Image.open(p), p.stem) for p in args.imagens]
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    montar(itens, args.colunas, (216, 384)).save(args.saida, optimize=True)
    print(args.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
