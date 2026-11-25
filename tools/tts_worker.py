"""Chatterbox Multilingual worker. Runs inside .venv-tts (torch 2.6 + CUDA, numpy<2), not the main venv.

Usage: .venv-tts/Scripts/python.exe tools/tts_worker.py JOB.json

JOB.json: {"lingua": "pt", "referencia": "path.wav" | null, "exaggeration": 0.5, "cfg_weight": 0.5,
           "temperature": 0.8, "whisper": "small", "itens": [{"texto": "...", "wav": "out.wav", "json": "out.json"}]}
For each item: synthesize, transcribe with faster-whisper (word timestamps), map the words back onto the
script text, retry with another seed if the transcript drifts from the text (Chatterbox sometimes repeats
or skips words), and write a 48 kHz mono 16-bit WAV plus [{"texto", "inicio", "fim"}].
Prints one JSON line per item: {"i": n, "seg": duration, "similaridade": s, "tentativas": k}.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

SR_SAIDA = 48000
SIMILARIDADE_MIN = 0.82
TENTATIVAS = 3


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if c.isalnum() and not unicodedata.combining(c))


def _mapear(texto: str, whisper_palavras: list[tuple[str, float, float]]) -> list[dict]:
    """Script words with times taken from the matching whisper words (interpolated where unmatched)."""
    alvo = re.findall(r"\S+", texto)
    a = [_norm(w) for w in alvo]
    b = [_norm(w[0]) for w in whisper_palavras]
    tempos: list[tuple[float, float] | None] = [None] * len(alvo)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                _, ini, fim = whisper_palavras[j1 + k]
                tempos[i1 + k] = (ini, fim)
        elif op == "replace" and j2 > j1:  # spread the whisper span over the script words
            ini, fim = whisper_palavras[j1][1], whisper_palavras[j2 - 1][2]
            n = i2 - i1
            for k in range(n):
                tempos[i1 + k] = (ini + (fim - ini) * k / n, ini + (fim - ini) * (k + 1) / n)
    fim_total = whisper_palavras[-1][2] if whisper_palavras else 0.5
    out, ultimo = [], 0.0
    for k, w in enumerate(alvo):  # fill gaps by interpolating between known neighbours
        if tempos[k] is None:
            prox = next((tempos[j][0] for j in range(k + 1, len(alvo)) if tempos[j]), fim_total)
            faltam = next((j for j in range(k + 1, len(alvo)) if tempos[j]), len(alvo)) - k
            passo = max(0.05, (prox - ultimo) / (faltam + 1))
            tempos[k] = (ultimo, ultimo + passo)
        ini, fim = tempos[k]
        ini = max(ini, ultimo)
        fim = max(fim, ini + 0.04)
        out.append({"texto": w.strip(".,!?;:\"'()"), "inicio": round(ini, 4), "fim": round(fim, 4)})
        ultimo = ini
    return out


def _salvar(caminho: Path, amostras: np.ndarray) -> None:
    pcm = (np.clip(amostras, -1.0, 1.0) * 32767).astype("<i2")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR_SAIDA)
        w.writeframes(pcm.tobytes())


def main(job_path: str) -> int:
    import librosa
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    from faster_whisper import WhisperModel

    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    whisper = WhisperModel(job.get("whisper", "small"), device=dev,
                           compute_type="float16" if dev == "cuda" else "int8")
    ref = job.get("referencia")
    for i, item in enumerate(job["itens"]):
        texto = item["texto"]
        melhor = None
        for k in range(TENTATIVAS):
            torch.manual_seed(1234 + 97 * k)
            wav = modelo.generate(texto, language_id=job.get("lingua", "pt"), audio_prompt_path=ref,
                                  exaggeration=job.get("exaggeration", 0.5), cfg_weight=job.get("cfg_weight", 0.5),
                                  temperature=job.get("temperature", 0.8))
            amostras = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
            a16 = librosa.resample(amostras, orig_sr=modelo.sr, target_sr=16000)
            segs, _ = whisper.transcribe(a16, language="pt", word_timestamps=True, beam_size=5,
                                         initial_prompt=texto, vad_filter=False)
            palavras = [(w.word.strip(), w.start, w.end) for s in segs for w in (s.words or [])]
            sim = difflib.SequenceMatcher(a=_norm(texto), b=_norm(" ".join(p[0] for p in palavras))).ratio()
            if melhor is None or sim > melhor[0]:
                melhor = (sim, amostras, palavras, k + 1)
            if sim >= SIMILARIDADE_MIN:
                break
        sim, amostras, palavras, tent = melhor
        pico = float(np.max(np.abs(amostras))) or 1.0
        saida = librosa.resample(amostras, orig_sr=modelo.sr, target_sr=SR_SAIDA) * min(1.0, 0.95 / pico)
        _salvar(Path(item["wav"]), saida)
        Path(item["json"]).write_text(json.dumps(_mapear(texto, palavras), ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"i": i, "seg": round(len(saida) / SR_SAIDA, 3), "similaridade": round(sim, 3),
                          "tentativas": tent}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
