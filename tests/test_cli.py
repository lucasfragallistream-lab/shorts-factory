import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import config
import main
from schemas import listar_fallbacks

RAIZ = Path(__file__).resolve().parent.parent


def _rodar(*args):
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.run([sys.executable, str(RAIZ / "main.py"), *args], cwd=RAIZ, env=env,
                          capture_output=True, text=True, encoding="utf-8")


@pytest.mark.parametrize("nome", listar_fallbacks())
def test_aceite_somente_validar(nome):
    proc = _rodar("--fallback", nome, "--somente-validar")
    assert proc.returncode == 0, proc.stderr
    assert "ranking OK" in proc.stdout and "fora do alvo" not in proc.stdout
    assert "Traceback" not in proc.stderr


def test_parser_opcoes():
    a = main.criar_parser().parse_args(
        ["--fallback", "crises", "--duracao", "61", "--tts", "mock", "--saida", "output/a.mp4", "--seed", "7",
         "--sem-bgm", "--encoder", "libx264", "--previa", "5"])
    assert (a.fallback, a.tts, a.seed, a.sem_bgm, a.duracao, a.previa) == ("crises", "mock", 7, True, 61.0, 5.0)
    padrao = main.criar_parser().parse_args([])
    assert padrao.duracao == config.DURACAO_ALVO and padrao.tts == config.TTS_PADRAO == "chatterbox"


def test_fontes_exclusivas():
    proc = _rodar("--fallback", "crises", "--tema", "x", "--somente-validar")
    assert proc.returncode == 2 and "Traceback" not in proc.stderr


def test_modo_antigo_removido():
    proc = _rodar("--modo", "idiota", "--fallback", "crises", "--somente-validar")
    assert proc.returncode == 2 and "Traceback" not in proc.stderr


@pytest.mark.parametrize(
    "args,trecho",
    [
        (["--fallback", "crises", "--duracao", "45", "--somente-validar"], "abaixo do mínimo"),
        (["--ranking", "nao_existe.json", "--somente-validar"], "não encontrado"),
        (["--somente-validar"], "informe --fallback"),
        (["--fallback", "nao_existe", "--somente-validar"], "disponíveis: crises"),
        (["--fallback", "crises", "--previa", "0"], "maior que zero"),
        (["--fallback", "crises", "--saida", "x.avi", "--somente-validar"], ".mp4"),
    ],
)
def test_erros_claros(args, trecho, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "LOGS", tmp_path)
    monkeypatch.setattr(config, "ULTIMO_ERRO", tmp_path / "ultimo_erro.txt")
    assert main.main(args) == 1
    assert trecho in capsys.readouterr().err
    assert trecho in (tmp_path / "ultimo_erro.txt").read_text(encoding="utf-8")


def test_ranking_invalido(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "LOGS", tmp_path)
    monkeypatch.setattr(config, "ULTIMO_ERRO", tmp_path / "ultimo_erro.txt")
    ruim = tmp_path / "ruim.json"
    ruim.write_text('{"titulo": "x"}', encoding="utf-8")
    assert main.main(["--ranking", str(ruim), "--somente-validar"]) == 1
    assert "ranking inválido" in capsys.readouterr().err


def test_so_audio_mock(tmp_path):
    saida = tmp_path / "ep.mp4"
    proc = _rodar("--fallback", "salario", "--so-audio", "--tts", "mock", "--saida", str(saida))
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "ep_voz.wav").exists()
    tl = json.loads((tmp_path / "ep_timeline.json").read_text(encoding="utf-8"))
    assert len(tl["segmentos"]) == 8  # opening, 5 items, cta, closing
    assert "61.000 s" in proc.stdout and "Warning" not in proc.stderr


def test_video_previa_mock(tmp_path):
    saida = tmp_path / "v.mp4"
    proc = _rodar("--fallback", "crises", "--tts", "mock", "--previa", "1", "--sem-bgm", "--saida", str(saida))
    assert proc.returncode == 0, proc.stderr
    assert saida.exists() and "1080x1920 30 fps" in proc.stdout and "30 quadros" in proc.stdout
