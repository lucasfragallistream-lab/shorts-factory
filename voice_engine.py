"""Narration: pluggable TTS engines, duration fitting, per-item timeline.json.

Engines
- edge: edge-tts with boundary="WordBoundary" (per-word timestamps), cached by
  hash of engine + text + voice + rate + pitch in cache/tts/.
- mock: offline synthetic "speech" with exact word timestamps (tests, quick runs).
- chatterbox: Chatterbox Multilingual pt (MIT) on the GPU via tools/tts_worker.py in .venv-tts,
  word times from faster-whisper alignment.

One narrator reads the ranking in segments (opening, each item, closing).
Duration (plan, section 6, item 1): every segment is trimmed to its words, then the
pauses grow (up to +0.3 s each) or shrink, speech is sped up with atempo (max 8%)
and a final "respiro" fills the rest so the track is exactly `alvo` seconds.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import tempfile
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

import config
import ffmpeg_utils
from schemas import Ranking, contar_palavras

SR = 48000
CACHE_TTS = config.CACHE / "tts"
MARGEM_INICIO = 0.05  # kept before the first word of a line
MARGEM_FIM = 0.12  # kept after the last word of a line
INICIO_PADRAO = 0.15  # first line starts here (the 0-2 s hook plays over it)
PAUSA_MIN = 0.08
PAUSA_EXTRA_MAX = 0.30
RESPIRO_MIN = 0.40
ATEMPO_MAX = 1.08


class ErroVoz(RuntimeError):
    """TTS failure (network, service, conversion)."""


class ErroDuracao(RuntimeError):
    """Speech does not fit the target duration even with the allowed speed-up."""


@dataclass
class Palavra:
    texto: str
    inicio: float
    fim: float


@dataclass
class Audio:
    """One synthesized line: mono float32 samples at SR, word times relative to the start."""

    amostras: np.ndarray
    palavras: list[Palavra] = field(default_factory=list)

    @property
    def duracao(self) -> float:
        return len(self.amostras) / SR


def voz_narrador() -> dict:
    c = config.NARRADOR
    return {"voz": c["voz"], "rate": c["rate"], "pitch": c["pitch"]}


def _chave(motor: str, texto: str, voz: dict) -> str:
    bruto = json.dumps([motor, texto, voz["voz"], voz["rate"], voz["pitch"]], ensure_ascii=False)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:24]


# --- WAV I/O ---------------------------------------------------------------
def ler_wav(caminho: Path) -> np.ndarray:
    with wave.open(str(caminho), "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1 or w.getframerate() != SR:
            raise ErroVoz(f"WAV inesperado em {caminho} (esperado 16 bits, mono, {SR} Hz)")
        dados = w.readframes(w.getnframes())
    return np.frombuffer(dados, dtype="<i2").astype(np.float32) / 32768.0


def salvar_wav(caminho: Path, amostras: np.ndarray) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(np.nan_to_num(amostras), -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return caminho


def _aparar(amostras: np.ndarray, palavras: list[Palavra]) -> Audio:
    """Cut leading/trailing silence around the words, shifting word times."""
    if not palavras:
        return Audio(amostras.astype(np.float32), [])
    ini = max(0.0, palavras[0].inicio - MARGEM_INICIO)
    fim = min(len(amostras) / SR, palavras[-1].fim + MARGEM_FIM)
    a, b = int(round(ini * SR)), int(round(fim * SR))
    novas = [Palavra(p.texto, round(p.inicio - ini, 4), round(min(p.fim, fim) - ini, 4)) for p in palavras]
    return Audio(amostras[a:b].astype(np.float32), novas)


def _fator_rate(rate: str) -> float:
    m = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)%", rate.strip())
    return 1.0 + float(m.group(1)) / 100 if m else 1.0


def _hz(pitch: str) -> float:
    m = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)Hz", pitch.strip())
    return float(m.group(1)) if m else 0.0


# --- engines ---------------------------------------------------------------
class MotorMock:
    """Deterministic offline engine: harmonic buzz per word, exact timestamps."""

    nome = "mock"

    def sintetizar(self, texto: str, voz: dict) -> Audio:
        # calibrated on edge (3.10 words/s); follows the configured narrator pace so scripts sized for the
        # default voice also fit in offline tests
        rate = _fator_rate(voz["rate"]) * config.NARRADOR["palavras_por_segundo"] / 3.10
        f0 = (210.0 if "Francisca" in voz["voz"] or "Thalita" in voz["voz"] else 120.0) + _hz(voz["pitch"])
        partes, palavras, t = [np.zeros(int(0.1 * SR), np.float32)], [], 0.1
        for w in re.findall(r"\S+", texto):
            letras = sum(ch.isalnum() for ch in w)
            dur = (0.045 * letras + 0.07) / rate
            n = int(dur * SR)
            tt = np.arange(n) / SR
            env = np.clip(np.sin(np.pi * np.arange(n) / max(n - 1, 1)), 0.0, 1.0) ** 0.6
            silabas = 0.55 + 0.45 * np.abs(np.sin(np.pi * tt * 4.5 * rate))
            sinal = sum(np.sin(2 * np.pi * f0 * k * tt) / k for k in (1, 2, 3))
            partes.append((0.35 * env * silabas * sinal).astype(np.float32))
            palavras.append(Palavra(w.strip(".,!?;:\"'"), round(t, 4), round(t + dur, 4)))
            gap = 0.05 / rate + (0.12 if w[-1] in ".!?" else 0.0)
            partes.append(np.zeros(int(gap * SR), np.float32))
            t += dur + gap
        partes.append(np.zeros(int(0.1 * SR), np.float32))
        return _aparar(np.concatenate(partes), palavras)

    def sintetizar_lote(self, itens: list[tuple[str, dict]]) -> list[Audio]:
        return [self.sintetizar(t, v) for t, v in itens]


class MotorEdge:
    """edge-tts (online). Raw audio + word boundaries cached per text/voice/rate/pitch."""

    nome = "edge"
    tentativas = 3
    concorrencia = 4

    def __init__(self, pasta_cache: Path = CACHE_TTS):
        self.cache = Path(pasta_cache)

    def _arquivos(self, texto, voz):
        base = self.cache / _chave(self.nome, texto, voz)
        return base.with_suffix(".mp3"), base.with_suffix(".wav"), base.with_suffix(".json")

    async def _baixar(self, texto: str, voz: dict, mp3: Path, js: Path) -> None:
        import edge_tts

        erro = None
        for n in range(self.tentativas):
            try:
                com = edge_tts.Communicate(texto, voz["voz"], rate=voz["rate"], pitch=voz["pitch"],
                                           boundary="WordBoundary")
                audio, palavras = bytearray(), []
                async for ch in com.stream():
                    if ch["type"] == "audio":
                        audio.extend(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        ini = ch["offset"] / 1e7
                        palavras.append({"texto": ch["text"], "inicio": round(ini, 4),
                                         "fim": round(ini + ch["duration"] / 1e7, 4)})
                if not audio or not palavras:
                    raise ErroVoz("edge-tts devolveu áudio ou timestamps vazios")
                mp3.write_bytes(bytes(audio))
                js.write_text(json.dumps(palavras, ensure_ascii=False), encoding="utf-8")
                return
            except Exception as exc:  # network / service errors: retry with backoff
                erro = exc
                await asyncio.sleep(1.5 * (n + 1))
        raise ErroVoz(f"edge-tts falhou após {self.tentativas} tentativas ({erro}); "
                      f"confira a internet ou use --tts mock")

    async def _baixar_faltantes(self, faltantes):
        sem = asyncio.Semaphore(self.concorrencia)

        async def um(item):
            async with sem:
                await self._baixar(*item)

        await asyncio.gather(*(um(i) for i in faltantes))

    def sintetizar_lote(self, itens: list[tuple[str, dict]]) -> list[Audio]:
        self.cache.mkdir(parents=True, exist_ok=True)
        faltantes = []
        for texto, voz in itens:
            mp3, wav, js = self._arquivos(texto, voz)
            if not (wav.exists() and js.exists()) and not (mp3.exists() and js.exists()):
                faltantes.append((texto, voz, mp3, js))
        if faltantes:
            asyncio.run(self._baixar_faltantes(faltantes))
        saida = []
        for texto, voz in itens:
            mp3, wav, js = self._arquivos(texto, voz)
            if not wav.exists():
                ffmpeg_utils.run_ffmpeg(["-y", "-i", str(mp3), "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le",
                                         str(wav)])
            palavras = [Palavra(**p) for p in json.loads(js.read_text(encoding="utf-8"))]
            saida.append(_aparar(ler_wav(wav), palavras))
        return saida

    def sintetizar(self, texto: str, voz: dict) -> Audio:
        return self.sintetizar_lote([(texto, voz)])[0]


class MotorChatterbox:
    """Chatterbox Multilingual (pt, MIT) on the GPU, run by tools/tts_worker.py inside .venv-tts.

    Word times come from faster-whisper alignment (done by the worker). Cached like edge, keyed by
    text + voice settings (+ reference voice file hash).
    """

    nome = "chatterbox"

    def __init__(self, pasta_cache: Path = CACHE_TTS):
        self.cache = Path(pasta_cache)
        self.cfg = dict(config.CHATTERBOX)
        ref = config.VOZES / "narrador.wav"
        self.referencia = ref if ref.exists() else None

    def _voz(self) -> dict:
        ref = hashlib.sha256(self.referencia.read_bytes()).hexdigest()[:12] if self.referencia else "padrao"
        params = f"{ref}|{self.cfg['exaggeration']}|{self.cfg['cfg_weight']}|{self.cfg['temperature']}"
        return {"voz": f"chatterbox:{params}", "rate": "+0%", "pitch": "+0Hz"}

    def _arquivos(self, texto):
        base = self.cache / _chave(self.nome, texto, self._voz())
        return base.with_suffix(".wav"), base.with_suffix(".json")

    def sintetizar_lote(self, itens: list[tuple[str, dict]]) -> list[Audio]:
        import subprocess

        self.cache.mkdir(parents=True, exist_ok=True)
        faltantes = []
        for texto, _ in itens:
            wav, js = self._arquivos(texto)
            if not (wav.exists() and js.exists()) and texto not in [f["texto"] for f in faltantes]:
                faltantes.append({"texto": texto, "wav": str(wav), "json": str(js)})
        if faltantes:
            py = config.RAIZ / ".venv-tts" / "Scripts" / "python.exe"
            if not py.exists():
                raise ErroVoz("motor chatterbox não instalado (.venv-tts ausente); veja docs/PLANO.md, fase R3, "
                              "ou use --tts edge")
            job = {"lingua": "pt", "referencia": str(self.referencia) if self.referencia else None,
                   "whisper": config.WHISPER_MODELO, "itens": faltantes, **self.cfg}
            arq = self.cache / f"job_{_chave(self.nome, json.dumps(faltantes), self._voz())}.json"
            arq.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            log = config.LOGS / "tts_worker.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as fh:
                proc = subprocess.run([str(py), str(config.RAIZ / "tools" / "tts_worker.py"), str(arq)],
                                      stdout=fh, stderr=subprocess.STDOUT, env={**__import__("os").environ,
                                                                                "PYTHONUTF8": "1"})
            arq.unlink(missing_ok=True)
            if proc.returncode != 0:
                raise ErroVoz(f"chatterbox falhou (código {proc.returncode}); veja {log}")
        saida = []
        for texto, _ in itens:
            wav, js = self._arquivos(texto)
            palavras = [Palavra(**p) for p in json.loads(js.read_text(encoding="utf-8"))]
            saida.append(_aparar(ler_wav(wav), palavras))
        return saida

    def sintetizar(self, texto: str, voz: dict) -> Audio:
        return self.sintetizar_lote([(texto, voz)])[0]


MOTORES = {"edge": MotorEdge, "mock": MotorMock, "chatterbox": MotorChatterbox}


def criar_motor(nome: str):
    if nome not in MOTORES:
        raise ValueError(f"motor de voz desconhecido: {nome} (disponíveis: {', '.join(MOTORES)})")
    return MOTORES[nome]()


# --- duration fitting ------------------------------------------------------
@dataclass
class PlanoDuracao:
    inicio: float
    pausas: list[float]
    atempo: float
    respiro: float
    alvo: float


def planejar_duracao(duracoes: list[float], alvo: float = config.DURACAO_ALVO,
                     inicio: float = INICIO_PADRAO, pausa: float = config.PAUSA_ENTRE_SEGMENTOS) -> PlanoDuracao:
    """Choose pauses, speed-up and final breath so the track is exactly `alvo` seconds."""
    if alvo < config.DURACAO_MINIMA:
        raise ErroDuracao(f"duração {alvo} s abaixo da trava de {config.DURACAO_MINIMA} s")
    fala, gaps = float(sum(duracoes)), max(len(duracoes) - 1, 0)
    livre = alvo - inicio - fala - RESPIRO_MIN  # room for the pauses
    if livre >= gaps * pausa:  # short or exact: longer pauses, then final breath
        extra = min(PAUSA_EXTRA_MAX, (livre - gaps * pausa) / gaps) if gaps else 0.0
        p = pausa + extra
        return PlanoDuracao(inicio, [round(p, 4)] * gaps, 1.0, round(alvo - inicio - fala - gaps * p, 4), alvo)
    if gaps and livre >= gaps * PAUSA_MIN:  # slightly long: shorter pauses
        return PlanoDuracao(inicio, [round(livre / gaps, 4)] * gaps, 1.0, RESPIRO_MIN, alvo)
    disponivel = alvo - inicio - RESPIRO_MIN - gaps * PAUSA_MIN
    fator = fala / disponivel
    if fator > ATEMPO_MAX:
        raise ErroDuracao(f"a fala tem {fala:.1f} s e não cabe em {alvo} s nem acelerando {ATEMPO_MAX:.0%}; "
                          f"encurte o roteiro")
    return PlanoDuracao(inicio, [PAUSA_MIN] * gaps, round(fator, 5), RESPIRO_MIN, alvo)


def aplicar_atempo(audio: Audio, fator: float) -> Audio:
    """Speed up keeping pitch (FFmpeg atempo); word times scale by 1/fator."""
    if abs(fator - 1.0) < 1e-6:
        return audio
    with tempfile.TemporaryDirectory() as tmp:
        ent, sai = Path(tmp) / "in.wav", Path(tmp) / "out.wav"
        salvar_wav(ent, audio.amostras)
        ffmpeg_utils.run_ffmpeg(["-y", "-i", str(ent), "-filter:a", f"atempo={fator:.5f}", "-ar", str(SR),
                                 "-ac", "1", "-c:a", "pcm_s16le", str(sai)])
        amostras = ler_wav(sai)
    palavras = [Palavra(p.texto, round(p.inicio / fator, 4), round(p.fim / fator, 4)) for p in audio.palavras]
    return Audio(amostras, palavras)


# --- energy ----------------------------------------------------------------
def rms_por_frame(amostras: np.ndarray, n_frames: int, fps: int = config.FPS) -> np.ndarray:
    passo = SR / fps
    out = np.zeros(n_frames, np.float32)
    for i in range(n_frames):
        seg = amostras[int(round(i * passo)):int(round((i + 1) * passo))]
        if len(seg):
            out[i] = float(np.sqrt(np.mean(seg.astype(np.float64) ** 2)))
    return out


def energia_suave(rms: np.ndarray) -> np.ndarray:
    """0..1 narrator energy per frame (normalized by the 95th percentile of voiced frames, smoothed)."""
    voz = rms[rms > 1e-4]
    ref = float(np.percentile(voz, 95)) if len(voz) else 0.0
    norm = np.clip(rms / ref, 0.0, 1.0) if ref > 0 else np.zeros_like(rms)
    out = np.copy(norm)
    for k in range(1, len(out)):
        out[k] = 0.5 * norm[k] + 0.5 * out[k - 1]
    return out


# --- whole episode ---------------------------------------------------------
@dataclass
class ResultadoAudio:
    wav: Path
    timeline: Path
    duracao: float
    plano: PlanoDuracao


def gerar_audio(ranking: Ranking, motor, alvo: float, wav_saida: Path, timeline_saida: Path,
                fps: int = config.FPS) -> ResultadoAudio:
    """Narrate the ranking and write the mono WAV (exactly `alvo` s) plus timeline.json.

    timeline: segmentos (tipo, item, rotulo, texto, times, frames, palavras), item_atual per frame
    (-1 = opening, 0..N-1 = item, N = closing), energia per frame, ranking (full JSON), plano."""
    segs = ranking.segmentos()
    voz = voz_narrador()
    audios = motor.sintetizar_lote([(s.texto, voz) for s in segs])
    plano = planejar_duracao([a.duracao for a in audios], alvo)
    audios = [aplicar_atempo(a, plano.atempo) for a in audios]

    total = int(round(alvo * SR))
    n_frames = int(round(alvo * fps))
    mix = np.zeros(total, np.float32)
    segs_tl, t = [], plano.inicio
    for i, (seg, audio) in enumerate(zip(segs, audios)):
        ini = int(round(t * SR))
        trecho = audio.amostras[: max(0, total - ini)]
        mix[ini:ini + len(trecho)] += trecho
        fim = t + audio.duracao
        segs_tl.append({
            "indice": i, "tipo": seg.tipo, "item": seg.item, "rotulo": seg.rotulo, "texto": seg.texto,
            "visuais": [v.model_dump() for v in seg.visuais],
            "inicio": round(t, 4), "fim": round(fim, 4),
            "frame_inicio": int(t * fps), "frame_fim": min(n_frames, int(np.ceil(fim * fps))),
            "palavras": [{"texto": p.texto, "inicio": round(t + p.inicio, 4), "fim": round(t + p.fim, 4)}
                         for p in audio.palavras],
        })
        t = fim + (plano.pausas[i] if i < len(plano.pausas) else 0.0)
    if segs_tl[-1]["fim"] > alvo + 1e-3:
        raise ErroDuracao(f"narração termina em {segs_tl[-1]['fim']:.2f} s, depois do alvo {alvo} s")
    plano.respiro = round(alvo - segs_tl[-1]["fim"], 4)

    n_itens = len(ranking.itens)
    item_atual = [-1] * n_frames
    for k, s in enumerate(segs_tl):
        if s["tipo"] == "abertura":
            continue
        valor = s["item"] if s["tipo"] == "item" else n_itens
        for f in range(s["frame_inicio"], n_frames):
            item_atual[f] = valor
    energia = energia_suave(rms_por_frame(mix, n_frames, fps))

    salvar_wav(wav_saida, mix)
    timeline = {
        "versao": 2, "fps": fps, "duracao": alvo, "frames": n_frames, "sample_rate": SR,
        "audio": str(Path(wav_saida).resolve()), "motor": motor.nome,
        "titulo": ranking.titulo, "layout": ranking.layout, "ranking": ranking.model_dump(),
        "plano": asdict(plano), "segmentos": segs_tl, "item_atual": item_atual,
        "energia": [round(float(e), 3) for e in energia],
    }
    Path(timeline_saida).parent.mkdir(parents=True, exist_ok=True)
    Path(timeline_saida).write_text(json.dumps(timeline, ensure_ascii=False), encoding="utf-8")
    return ResultadoAudio(Path(wav_saida), Path(timeline_saida), len(mix) / SR, plano)


def medir_palavras_por_segundo(rankings: list[Ranking], motor) -> float:
    """Narrator words per second of trimmed speech over every segment of the given rankings."""
    textos = [s.texto for r in rankings for s in r.segmentos()]
    audios = motor.sintetizar_lote([(tx, voz_narrador()) for tx in textos])
    return round(sum(contar_palavras(tx) for tx in textos) / sum(a.duracao for a in audios), 3)
