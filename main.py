"""Shorts Factory CLI: ranking -> narration -> frames -> MP4.

Pivot to rankings (docs/PLANO.md, section 0): R1 loads/validates rankings and narrates them
(--so-audio), R4 assembles the video (montagem.py) and the Gemini writer arrives in R5.
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

import config


class ErroUsuario(Exception):
    """Expected error: shown as a short message, no traceback."""


def criar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Gera um vídeo vertical 1080x1920 de 61,0 s de ranking com narrador (\"As 4 crises que...\").",
    )
    fonte = p.add_mutually_exclusive_group()
    fonte.add_argument("--fallback", metavar="NOME",
                       help="ranking local de assets/rankings/NOME.json (ex.: crises, salario)")
    fonte.add_argument("--ranking", type=Path, metavar="ARQ", help="caminho de um ranking JSON")
    fonte.add_argument("--tema", help="tema para o roteirista Gemini (gera o ranking e salva em output/rankings/)")
    p.add_argument("--duracao", type=float, default=config.DURACAO_ALVO,
                   help=f"duração final em segundos (padrão {config.DURACAO_ALVO}, mínimo {config.DURACAO_MINIMA})")
    p.add_argument("--tts", choices=config.TTS_MOTORES, default=config.TTS_PADRAO, help="motor de voz")
    p.add_argument("--saida", type=Path, help="arquivo MP4 de saída")
    p.add_argument("--seed", type=int, help="semente para escolhas aleatórias")
    p.add_argument("--sem-bgm", action="store_true", help="não mixar música de fundo")
    p.add_argument("--sem-sfx", action="store_true", help="sem efeitos sonoros (whoosh, pop, impacto)")
    p.add_argument("--somente-validar", action="store_true", help="só carrega e valida o ranking")
    p.add_argument("--so-audio", action="store_true", help="gera só a narração (WAV) e o timeline.json")
    p.add_argument("--encoder", choices=("auto", "h264_nvenc", "libx264"), default="auto",
                   help="codificador de vídeo (auto: NVENC se disponível)")
    p.add_argument("--previa", type=float, metavar="SEG",
                   help="renderiza só os primeiros SEG segundos do vídeo (teste rápido)")
    return p


def validar_args(args: argparse.Namespace) -> None:
    if args.duracao < config.DURACAO_MINIMA:
        raise ErroUsuario(f"--duracao {args.duracao} abaixo do mínimo de {config.DURACAO_MINIMA} s")
    if args.previa is not None and args.previa <= 0:
        raise ErroUsuario("--previa precisa ser maior que zero")
    if args.saida is not None and args.saida.suffix.lower() != ".mp4":
        raise ErroUsuario(f"--saida precisa terminar em .mp4 (recebido: {args.saida})")


def obter_ranking(args: argparse.Namespace):
    from pydantic import ValidationError

    from schemas import Ranking, listar_fallbacks

    if args.ranking:
        caminho = args.ranking
    elif args.fallback:
        caminho = config.RANKINGS / f"{args.fallback}.json"
        if not caminho.exists():
            raise ErroUsuario(f"ranking de fallback '{args.fallback}' não existe; "
                              f"disponíveis: {', '.join(listar_fallbacks()) or 'nenhum'}")
    elif args.tema:
        return gerar_por_tema(args)
    else:
        raise ErroUsuario("informe --fallback NOME, --ranking ARQ ou --tema")

    if not caminho.exists():
        raise ErroUsuario(f"ranking não encontrado: {caminho}")
    try:
        return Ranking.carregar(caminho)
    except ValidationError as exc:
        raise ErroUsuario(f"ranking inválido em {caminho}:\n{exc}") from exc
    except ValueError as exc:  # JSON malformado
        raise ErroUsuario(f"JSON inválido em {caminho}: {exc}") from exc


def slug(texto: str) -> str:
    import re
    import unicodedata

    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:40] or "tema"


def gerar_por_tema(args: argparse.Namespace):
    import json

    import script_generator as sg

    res = sg.gerar(args.tema, seed=args.seed, log=lambda m: print(f"roteirista: {m}"))
    destino = config.RANKINGS_GERADOS / f"{slug(args.tema)}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(res.ranking.model_dump(exclude_none=True), ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(f"ranking ({res.origem}): {destino}")
    return res.ranking


def resumo_ranking(ranking) -> str:
    # no "out of target" warning here: the words/s estimate is unreliable (names, spelled-out numbers);
    # the real fit is decided on the synthesized audio (voice_engine / script_generator.checar_fala_real)
    fala = ranking.duracao_fala_estimada()
    rotulos = ", ".join(it.rotulo for it in ranking.itens)
    return (f"ranking OK: {ranking.titulo!r} | layout {ranking.layout} | {len(ranking.itens)} itens ({rotulos}) | "
            f"{ranking.palavras} palavras | narração estimada ~{fala:.0f} s")


def registrar_erro(msg: str, detalhe: str = "") -> None:
    config.LOGS.mkdir(parents=True, exist_ok=True)
    texto = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n"
    if detalhe:
        texto += detalhe
    config.ULTIMO_ERRO.write_text(texto, encoding="utf-8")


def nome_base(args: argparse.Namespace) -> str:
    if args.fallback:
        return f"ranking_{args.fallback}"
    if args.ranking:
        return f"ranking_{args.ranking.stem}"
    if args.tema:
        return f"ranking_{slug(args.tema)}"
    return "ranking"


def caminhos_saida(args: argparse.Namespace) -> tuple[Path, Path]:
    saida = args.saida or (config.OUTPUT / f"{nome_base(args)}.mp4")
    return saida.with_name(saida.stem + "_voz.wav"), saida.with_name(saida.stem + "_timeline.json")


def gerar_narracao(args: argparse.Namespace, ranking):
    import ffmpeg_utils
    import voice_engine as ve

    wav, timeline = caminhos_saida(args)
    try:
        res = ve.gerar_audio(ranking, ve.criar_motor(args.tts), args.duracao, wav, timeline)
    except (ve.ErroVoz, ve.ErroDuracao, ffmpeg_utils.FFmpegError) as exc:
        raise ErroUsuario(str(exc)) from exc
    medida = ffmpeg_utils.duracao_midia(res.wav)
    p = res.plano
    print(f"áudio: {res.wav} ({medida:.3f} s) | timeline: {res.timeline}")
    print(f"plano: pausas {p.pausas[0] if p.pausas else 0:.2f} s | atempo {p.atempo:.3f} | "
          f"respiro final {p.respiro:.2f} s")
    if abs(medida - args.duracao) > 0.01 or medida < config.DURACAO_MINIMA:
        raise ErroUsuario(f"duração do áudio {medida:.3f} s difere do alvo {args.duracao} s")
    return res


def executar(args: argparse.Namespace) -> int:
    validar_args(args)
    ranking = obter_ranking(args)
    print(resumo_ranking(ranking))
    if args.somente_validar:
        return 0
    res = gerar_narracao(args, ranking)
    if args.so_audio:
        return 0
    montar_video(args, ranking, res.timeline)
    return 0


def buscar_fotos(ranking, saida: Path) -> dict:
    """Real photos per item (Wikimedia Commons, commercial-use licenses) + credits file for the description."""
    import imagens

    fotos, achadas = {}, []
    for i, it in enumerate(ranking.itens):
        if not it.imagem:
            continue
        try:
            f = imagens.buscar(it.imagem)
        except imagens.ErroImagem as exc:
            print(f"aviso: sem foto para '{it.rotulo}': {exc}")
            continue
        fotos[i] = f.arquivo
        achadas.append(f)
    if achadas:
        cred = imagens.creditos(achadas, saida.with_name(saida.stem + "_creditos.txt"))
        print(f"fotos: {len(achadas)} de {len(ranking.itens)} itens | créditos em {cred}")
    return fotos


def montar_video(args: argparse.Namespace, ranking, timeline_path: Path) -> Path:
    import bgm
    import ffmpeg_utils
    import video_assembler as va
    from montagem import Montagem, carregar_timeline

    saida = args.saida or (config.OUTPUT / f"{nome_base(args)}.mp4")
    tl = carregar_timeline(timeline_path)
    fotos = buscar_fotos(ranking, saida)
    mont = Montagem(ranking, tl, seed=args.seed or 0, fotos=fotos)
    n = tl["frames"] if args.previa is None else min(tl["frames"], round(args.previa * tl["fps"]))
    audio = saida.with_name(saida.stem + "_mix.wav")
    trilha = None if args.sem_bgm else bgm.obter_bgm(seed=args.seed or 0)
    voz = Path(tl["audio"])
    if not args.sem_sfx:  # sound effects summed with the narration, then mixed/normalized together
        import sfx
        import voice_engine as ve

        trilha_voz = ve.ler_wav(voz)
        efeitos = sfx.trilha_sfx(mont.eventos_sonoros(), len(trilha_voz) / ve.SR)
        voz = ve.salvar_wav(saida.with_name(saida.stem + "_voz_sfx.wav"), trilha_voz + efeitos[: len(trilha_voz)])
    try:
        va.mixar_audio(voz, audio, tl["duracao"], trilha)
        res = va.codificar(mont.quadro, n, audio, saida, encoder=args.encoder,
                           progresso=lambda i, tot: print(f"\rquadros {i}/{tot}", end="", flush=True))
        print()
        info = va.conferir_video(res.mp4)
    except (va.ErroMontagem, ffmpeg_utils.FFmpegError) as exc:
        raise ErroUsuario(str(exc)) from exc
    print(f"vídeo: {res.mp4} | {info['largura']}x{info['altura']} {info['fps']:.0f} fps | "
          f"{info['duracao']:.3f} s | {info['frames']} quadros | {res.encoder} | render {res.segundos_render:.0f} s")
    if args.previa is None and (info["duracao"] < config.DURACAO_MINIMA or (info["largura"], info["altura"]) != (1080, 1920)):
        raise ErroUsuario(f"vídeo fora do formato: {info}")
    return res.mp4


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = criar_parser().parse_args(argv)
    try:
        return executar(args)
    except ErroUsuario as exc:
        registrar_erro(str(exc))
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # unexpected: short message on screen, full traceback in the log
        registrar_erro(f"erro inesperado: {exc}", traceback.format_exc())
        print(f"ERRO inesperado: {exc} (detalhes em {config.ULTIMO_ERRO})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
