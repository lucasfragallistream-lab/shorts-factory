"""Sound design + event sheet for one "Você é o Maquinista" episode.

Usage: python tools/maquinista_som.py motion/trolley/src/ep2 motion/trolley/public/ep2
Reads <src>/timeline.json (voice words) and <src>/plano.json (camera keys anchored on words + the episode's sound
cues), writes:
  <src>/eventos.json   resolved camera keys, kicks, heartbeats, barks, lever pulls, sparks, silence... (the video syncs to it)
  <pub>/audio.wav      final mix at -14 LUFS (voice + real PD/CC0 effects + procedural effects + music bed)
  <pub>/creditos_sons.txt
Kit rules: the bed never stops (10-15 dB under the voice) except the planned silence drop before the punchline,
effects tucked under the voice, -14 LUFS master. Thriller layer (ep. 2 notes): metal screech + sparks before the first
word, rail clacks that speed up with the train, out-of-breath narrator, a riser into the twist, 1 s of total silence
on the twist line, a deafening whistle that cuts to silence on the final freeze.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import bgm  # noqa: E402
import sfx  # noqa: E402
import sons  # noqa: E402
import video_assembler as va  # noqa: E402
import voice_engine as ve  # noqa: E402
from ffmpeg_utils import find_ffmpeg  # noqa: E402

SR = ve.SR
DUR = 61.0
N = int(DUR * SR)
CAB = {"cab_ecu", "cab_mcu", "cab_shock", "cab_extreme", "lever_cu", "desvio_cu", "mao_alavanca", "olho_ecu"}
TREM = {"train_side", "wheels_low", "rails_skim", "roda_ecu", "trilho_frente", "final_switch", "approach", "approach_a",
        "approach_b"}
PERTO = CAB | TREM
FAISCA_POSES = {"rails_skim", "roda_ecu", "final_switch"}
TREM_PADRAO = {"v0": 22.0, "a": 0.2, "z_fim": 0.6}  # m/s, m/s², metres before the switch when the picture freezes
JUNTA = 7.0  # metres between rail joints (stylised: the clack-clack speeds up with the train)
_usados: set[str] = set()


def db(x: float) -> float:
    return 10 ** (x / 20)


def norm(x: np.ndarray, pico_db: float = -1.0) -> np.ndarray:
    return (x / (np.max(np.abs(x)) or 1) * db(pico_db)).astype(np.float32)


def ler(nome: str) -> np.ndarray:
    _usados.add(nome)
    return ve.ler_wav(sons.CACHE / f"{nome}.wav").astype(np.float32)


def trecho(x: np.ndarray, a: float, b: float, fade: float = 0.01) -> np.ndarray:
    y = x[int(a * SR):int(b * SR)].copy()
    f = min(int(fade * SR), len(y) // 2)
    if f:
        y[:f] *= np.linspace(0, 1, f)
        y[-f:] *= np.linspace(1, 0, f)
    return y


def reamostrar(x: np.ndarray, fator: float) -> np.ndarray:
    """Pitch/speed up by `fator` (>1 = higher and shorter), simple linear resampling."""
    idx = np.arange(0, len(x) - 1, fator)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


def por(mix: np.ndarray, x: np.ndarray, t: float, ganho_db: float = 0.0):
    i = int(t * SR)
    if i >= len(mix) or i + len(x) <= 0:
        return
    x = x * db(ganho_db)
    if i < 0:
        x, i = x[-i:], 0
    mix[i:i + len(x)] += x[: len(mix) - i]


def loop(x: np.ndarray, n: int) -> np.ndarray:
    return np.tile(x, n // len(x) + 1)[:n]


def envelope(pontos: list[tuple[float, float]], suave: float = 0.25) -> np.ndarray:
    """Gain curve (linear) from (t, dB) steps, smoothed over `suave` seconds."""
    t = np.arange(N) / SR
    alvo = np.full(N, db(pontos[0][1]), np.float32)
    for (a, g) in pontos:
        alvo[t >= a] = db(g)
    k = max(1, int(suave * SR))
    return np.convolve(alvo, np.ones(k, np.float32) / k, mode="same").astype(np.float32)


def grãos(x: np.ndarray, n: int, dur: float, min_gap: float = 0.25) -> list[np.ndarray]:
    """The n loudest onsets of x as short grains."""
    h = int(0.01 * SR)
    m = len(x) // h
    e = np.sqrt((x[: m * h].reshape(m, h) ** 2).mean(1))
    ordem = np.argsort(e)[::-1]
    escolhidos: list[int] = []
    for i in ordem:
        if all(abs(i - j) * 0.01 > min_gap for j in escolhidos):
            escolhidos.append(int(i))
        if len(escolhidos) == n:
            break
    return [norm(trecho(x, max(0, i * 0.01 - 0.03), i * 0.01 + dur, 0.008), -3) for i in sorted(escolhidos)]


# --- procedural layers (zero cost, no licence) -----------------------------------------------------
def _t(seg: float) -> np.ndarray:
    return np.arange(int(seg * SR)) / SR


def guincho(dur: float, seed: int = 1) -> np.ndarray:
    """Metal on metal: inharmonic partials with a nervous vibrato + bright hiss."""
    rng = np.random.default_rng(seed)
    t = _t(dur)
    vib = sfx._passa_baixa(rng.normal(size=len(t)).astype(np.float32), 0.0008)
    vib = vib / (np.max(np.abs(vib)) or 1)
    x = np.zeros(len(t), np.float32)
    for f, a in ((2150, 1.0), (3420, 0.7), (5230, 0.45), (7880, 0.25)):
        fi = f * (1 + 0.035 * vib + 0.01 * np.sin(2 * np.pi * 7.3 * t))
        x += a * np.sin(2 * np.pi * np.cumsum(fi) / SR).astype(np.float32)
    chiado = rng.normal(size=len(t)).astype(np.float32)
    chiado = chiado - sfx._passa_baixa(chiado, 0.25)
    am = 0.65 + 0.35 * np.abs(sfx._passa_baixa(rng.normal(size=len(t)).astype(np.float32), 0.004)) * 6
    x = (0.6 * x + 0.5 * chiado) * np.clip(am, 0, 1.4)
    f = min(int(0.05 * SR), len(x) // 4)
    x[:f] *= np.linspace(0, 1, f)
    x[-f * 3:] *= np.linspace(1, 0, f * 3)
    return norm(x, -1)


def estalos(dur: float, densidade: float, seed: int = 2) -> np.ndarray:
    """Spark crackle: sparse bright clicks."""
    rng = np.random.default_rng(seed)
    x = np.zeros(int(dur * SR), np.float32)
    for _ in range(int(dur * densidade)):
        i = int(rng.integers(0, max(1, len(x) - 400)))
        n = int(rng.integers(60, 300))
        x[i:i + n] += rng.normal(size=n).astype(np.float32) * np.exp(-np.arange(n) / (n / 4)) * float(rng.uniform(0.3, 1))
    x = x - sfx._passa_baixa(x, 0.3)
    return norm(x, -1)


def riser(dur: float, seed: int = 3) -> np.ndarray:
    """Long tension riser: noise opening up + a rising tone + a tremolo that speeds up, cut dead at the end."""
    rng = np.random.default_rng(seed)
    t = _t(dur)
    k = t / t[-1]
    ruido = sfx._passa_baixa(rng.normal(size=len(t)).astype(np.float32), 0.01 + 0.35 * k ** 2)
    f = 140 + 1500 * k ** 2.2
    tom = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.35 * np.sin(2 * np.pi * np.cumsum(f * 1.498) / SR)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(2 + 14 * k ** 2) / SR)
    x = (0.55 * tom + ruido * 2.2) * trem * k ** 2.4
    return norm(x.astype(np.float32), -1)


def clique(freq: float, dur: float = 0.06, seed: int = 4) -> np.ndarray:
    """A hard tile on a wooden table (domino)."""
    rng = np.random.default_rng(seed)
    t = _t(dur)
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t * 90) + 0.5 * np.sin(2 * np.pi * freq * 2.7 * t) * np.exp(-t * 140)
    x[: int(0.003 * SR)] += rng.normal(size=int(0.003 * SR)) * 0.8
    return norm(x.astype(np.float32), -1)


def amassado(dur: float = 0.7, seed: int = 5) -> np.ndarray:
    """Paper bag crinkle: short band-passed noise bursts."""
    rng = np.random.default_rng(seed)
    x = np.zeros(int(dur * SR), np.float32)
    for _ in range(int(dur * 38)):
        i, n = int(rng.integers(0, len(x) - 900)), int(rng.integers(200, 900))
        b = rng.normal(size=n).astype(np.float32) * np.hanning(n).astype(np.float32) * float(rng.uniform(0.2, 1))
        x[i:i + n] += b
    x = sfx._passa_baixa(x, 0.5) - sfx._passa_baixa(x, 0.06)
    return norm(x, -1)


# --- anchors -------------------------------------------------------------------------------------
def resolver(at, palavras: list[dict]) -> float:
    if isinstance(at, (int, float)):
        return float(at)
    nome, _, n = str(at).partition("#")
    n = int(n or 1)
    k = 0
    for w in palavras:
        if re.sub(r"[.,!?;:]", "", w["w"]) == nome:
            k += 1
            if k == n:
                return w["a"]
    raise SystemExit(f"âncora não encontrada: {at}")


def tempo_de(item: dict, palavras: list[dict], campo: str = "at") -> float:
    return round(resolver(item[campo], palavras) + float(item.get("off", 0.0)), 3)


def _juntas(trem: dict, congela: float) -> list[float]:
    """Times the front bogie hits a rail joint (accelerating train)."""
    v0, a = trem["v0"], trem["a"]
    s_fim = v0 * congela + a * congela ** 2 / 2
    out, k = [], 1
    while k * JUNTA < s_fim:
        out.append((-v0 + (v0 * v0 + 2 * a * k * JUNTA) ** 0.5) / a)
        k += 1
    return out


def _bgm_mudo(silencios: list[tuple[float, float]]) -> Path:
    """The music bed with the silence windows cut out (temporary WAV for mixar_audio)."""
    fonte = bgm.obter_bgm("tenso")
    tmp = Path(tempfile.mkdtemp()) / "bgm_mudo.wav"
    bruto = tmp.with_name("bgm.wav")
    subprocess.run([find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(fonte), "-ac", "1",
                    "-ar", str(SR), str(bruto)], check=True)
    x = loop(ve.ler_wav(bruto).astype(np.float32), N)
    ve.salvar_wav(tmp, x * mascara(silencios))
    return tmp


def mascara(silencios: list[tuple[float, float]], rampa: float = 0.015) -> np.ndarray:
    m = np.ones(N, np.float32)
    r = int(rampa * SR)
    for a, b in silencios:
        i, j = int(a * SR), min(N, int(b * SR))
        m[i:j] = 0
        m[max(0, i - r):i] = np.minimum(m[max(0, i - r):i], np.linspace(1, 0, i - max(0, i - r)))
        if j < N:
            m[j:j + r * 3] = np.minimum(m[j:j + r * 3], np.linspace(0, 1, len(m[j:j + r * 3])))
    return m


def _zerar_final(wav: Path, a: float):
    """Hard silence from `a` to the end (the whistle cuts to nothing)."""
    with wave.open(str(wav)) as w:
        p = w.getparams()
        x = np.frombuffer(w.readframes(p.nframes), np.int16).reshape(-1, p.nchannels).astype(np.float32)
    i, r = int(a * p.framerate), int(0.008 * p.framerate)
    x[i - r:i] *= np.linspace(1, 0, r)[:, None]
    x[i:] = 0
    with wave.open(str(wav), "wb") as w:
        w.setparams(p)
        w.writeframes(x.astype(np.int16).tobytes())


def _ligar_takes(keys: list[dict], manifesto: Path, src: Path, linhas: list[dict]):
    """Keys with "take" show a clean clip of an earlier episode (motion/trolley/takes.mjs) instead of the 3D world.
    The first key of a take window gives "de" (that episode's time shown at the key) or "alinha" (the id of a line
    both episodes say word for word: the clip is synced to it); the next keys with the same take keep the same offset.
    Writes clip/delta/clip_f0/clip_ate on each key and checks the clip covers the whole window."""
    bancos = json.loads(manifesto.read_text(encoding="utf-8")) if manifesto.exists() else {}
    delta: dict[str, float] = {}
    for i, k in enumerate(keys):
        nome = k.get("take")
        if not nome:
            continue
        if nome not in bancos:
            raise SystemExit(f"take '{nome}' não está no banco {manifesto}")
        if "alinha" in k:
            outra = json.loads((src.parent / bancos[nome]["ep"] / "timeline.json").read_text(encoding="utf-8"))["linhas"]
            a = next((x for x in linhas if x["id"] == k["alinha"]), None)
            b = next((x for x in outra if x["id"] == k["alinha"]), None)
            if not a or not b or a["texto"] != b["texto"]:
                raise SystemExit(f"take '{nome}': a fala '{k['alinha']}' precisa existir igual nos dois episódios")
            delta[nome] = a["a"] - b["a"]
        elif "de" in k:
            delta[nome] = k["t"] - float(k["de"])
        elif nome not in delta:
            raise SystemExit(f"a primeira chave do take '{nome}' precisa de 'de' ou 'alinha'")
        b, d = bancos[nome], delta[nome]
        fim = DUR
        if i + 1 < len(keys):  # the clip stops where the next 3D move starts (a fly/whip/travel leaves from this pose)
            nx = keys[i + 1]
            fim = nx["t"] if nx.get("take") or nx["move"] == "cut" else nx["t"] - nx.get("dur", 0.0)
        if k["t"] - d < b["de"] - 0.02 or fim - d > b["ate"] + 0.02:
            raise SystemExit(f"take '{nome}' cobre {b['de']}-{b['ate']} s, mas a janela pede "
                             f"{k['t'] - d:.2f}-{fim - d:.2f} s")
        k.update(clip=nome, delta=round(d, 4), clip_f0=b["f0"], clip_ate=round(fim, 4))


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    src, pub = Path(argv[0]), Path(argv[1])
    pub.mkdir(parents=True, exist_ok=True)
    tl = json.loads((src / "timeline.json").read_text(encoding="utf-8"))
    plano = json.loads((src / "plano.json").read_text(encoding="utf-8"))
    P = tl["palavras"]
    keys = [{**k, "t": tempo_de(k, P)} for k in plano["keys"]]
    keys.sort(key=lambda k: k["t"])
    _ligar_takes(keys, pub.parent / "takes" / "takes.json", src, tl["linhas"])
    pose_em = lambda t: next((k["pose"] for k in reversed(keys) if k["t"] - k.get("dur", 0) <= t), keys[0]["pose"])  # noqa: E731
    kicks = [[round(resolver(a, P), 3), amp] for a, amp in plano["kicks"]] + \
            [[k["t"], k["kick"]] for k in keys if k.get("kick")]
    puxadas = [round(resolver(a, P), 3) for a in plano["puxadas"]]
    solta = round(resolver(plano["solta"], P), 3)
    cont = tl["contagem"]
    congela = float(plano.get("congela", DUR))
    fim_som = float(plano.get("fim_som", DUR))
    trem = {**TREM_PADRAO, **plano.get("trem", {})}
    sil = plano.get("silencio")
    silencios = []
    if sil:
        s0 = resolver(sil["at"], P)
        silencios.append((round(s0 - sil["antes"], 3), round(s0 + sil["depois"], 3)))
    fim = [(fim_som, DUR)] if fim_som < DUR else []

    # heartbeat times: 74 -> 104 bpm while speaking, 110 -> 180 bpm in the countdown
    bpm_em = lambda t: 74 + 30 * t / cont if t < cont else 110 + 70 * (t - cont) / (DUR - cont)  # noqa: E731
    batidas, t = [], 0.05
    while t < min(DUR, fim_som) - 0.1:
        if not any(a <= t < b for a, b in silencios):
            batidas.append(round(t, 3))
        t += 60 / bpm_em(t)

    # sparks: always a little at speed, a shower on the hook, the pulls, the snap, the wheel inserts, the countdown
    g0 = tempo_de(plano["guincho"], P) if "guincho" in plano else 0.0  # the in-medias-res screech (0 s by default)
    faiscas = [[0.0, DUR, 0.22], [g0, g0 + 2.9, 1.0], [solta, solta + 1.0, 0.8], [cont, congela, 0.6]]
    faiscas += [[p, p + 0.7, 0.9] for p in puxadas]
    for i, k in enumerate(keys):
        if k["pose"] in FAISCA_POSES:
            fimk = keys[i + 1]["t"] if i + 1 < len(keys) else DUR
            faiscas.append([k["t"], fimk, 1.0])

    rng = np.random.default_rng(7)
    mix = np.zeros(N, np.float32)
    efeitos = np.zeros(N, np.float32)
    tt = np.arange(N) / SR

    # --- train bed: steam chuffs near/far by camera pose; rising in the countdown --------------------------
    vapor = norm(ler("steam_engine_ogg"), -3)
    pontos = []
    for k in keys:
        ini = k["t"] - k.get("dur", 0)
        pontos.append((max(0.0, ini), -9.0 if k["pose"] in PERTO else -24.0))
    pontos.sort()
    env = envelope(pontos, 0.2)
    sobe = np.clip((tt - cont) / (congela - cont), 0, 1)
    env = np.maximum(env, db(-20 + 14 * sobe) * (tt >= cont))  # the train closes in during the countdown
    efeitos += loop(vapor, N) * env
    ronco = sfx._passa_baixa(rng.normal(size=N).astype(np.float32), 0.02)
    efeitos += norm(ronco, -1) * db(-28) * (0.6 + 0.4 * np.clip(tt / congela, 0, 1))  # the bed never stops

    # rail joints: clack-clack (front bogie, then the drivers), faster and faster as the train speeds up
    juntas_x = grãos(norm(ler("rail_joint_sound_oer_hise_ogg")), 6, 0.16, 0.2)
    for j, tj in enumerate(_juntas(trem, congela)):
        v = trem["v0"] + trem["a"] * tj
        g = -6 if pose_em(tj) in PERTO else -19
        for d, extra in ((0.0, 0), (2.0 / v, -2), (4.3 / v, -4)):
            por(efeitos, juntas_x[(j + int(d * 10)) % len(juntas_x)], tj + d, g + extra + 4 * min(1, tj / congela))

    # hook in medias res: deafening metal screech + spark crackle BEFORE the first word
    por(efeitos, guincho(2.9, 11), g0, 1)
    por(efeitos, estalos(2.9, 60, 12), g0, -6)
    por(efeitos, sfx.som("impacto"), g0, 3)
    # sparks crackle wherever they fly on screen
    for a, b, inten in faiscas[1:]:
        if b - a > 0.05:
            por(efeitos, estalos(b - a, 40 * inten, int(a * 10)), a, -16 + 8 * inten)

    # whistle on the reveal, horn on the final question
    apito = norm(ler("parovoz_sound_ogg"), -1)
    if plano.get("apito_at"):
        por(efeitos, apito, resolver(plano["apito_at"], P) - 0.25, -5)
    buzina = norm(trecho(ler("airchime_k5la_ogg"), 0.6, 3.9, 0.05), -1)
    if plano.get("buzina_at"):
        por(efeitos, buzina, resolver(plano["buzina_at"], P) - 0.2, -8)

    # brake: pulls (metal clunk + screech), then the lever snaps
    for i, t in enumerate(puxadas):
        por(efeitos, sfx.som("impacto"), t, -3)
        por(efeitos, guincho(0.75, 20 + i), t + 0.04, -9)
    estalo = norm(sfx._passa_baixa(rng.normal(size=int(0.12 * SR)).astype(np.float32), 0.6) *
                  np.linspace(1, 0, int(0.12 * SR)), -1)
    por(efeitos, estalo, solta, -1)
    por(efeitos, sfx.som("impacto"), solta, 3)

    # heartbeat: louder on the driver, pounding in the countdown
    coracao = ler("human_heart_rate_flac")
    lub, dub = norm(trecho(coracao, 0.30, 0.62, 0.01), -1), norm(trecho(coracao, 0.66, 0.98, 0.01), -1)
    for t in batidas:
        perto = pose_em(t) in CAB or t >= cont
        g = -3 if t >= cont else (-8 if perto else -18)
        por(efeitos, lub, t, g)
        por(efeitos, dub, t + min(0.3, 60 / bpm_em(t) * 0.38), g - 3)

    # out of breath: a real inhale in each planned breath gap
    folego = grãos(norm(ler("heavy_breathing_3_ogg")), 6, 0.34, 0.6)
    for i, t in enumerate(tl.get("respiros", [])):
        por(efeitos, folego[i % len(folego)], t, -3)

    # the episode's own cues (dogs, dominoes, laughter, the paper bag...)
    latidos: list[list[float]] = []
    lat = None
    for c in plano.get("sons", []):
        kind = c["som"]
        if kind == "latidos":
            if lat is None:
                lat = grãos(norm(ler("dog_ogg")), 8, 0.32)
            t, b = tempo_de(c, P, "de"), tempo_de(c, P, "ate")
            while t < b:
                por(efeitos, reamostrar(lat[int(rng.integers(len(lat)))], c.get("tom", 1.0)), t, c.get("g", -10))
                latidos.append([round(t, 3), c.get("cao", 0)])
                t += c.get("passo", 0.45) * float(rng.uniform(0.7, 1.3))
        elif kind == "ganido":
            x = norm(ler("puppy_at_a_night_ogg"), -3)
            por(efeitos, reamostrar(trecho(x, 0, c.get("dur", 3.0) * c.get("tom", 1.0), 0.3), c.get("tom", 1.0)),
                tempo_de(c, P), c.get("g", -16))
        elif kind == "domino":
            t, b = tempo_de(c, P, "de"), tempo_de(c, P, "ate")
            while t < b:
                por(efeitos, clique(float(rng.uniform(2300, 3600)), seed=int(t * 100)), t, c.get("g", -14))
                t += float(rng.uniform(0.09, 0.42))
        elif kind == "batida":  # a tile slammed on the table
            t = tempo_de(c, P)
            por(efeitos, clique(1300, 0.12, 9), t, c.get("g", -2))
            por(efeitos, sfx.som("impacto"), t, c.get("g", -2) - 6)
        elif kind == "risada":
            x = norm(ler("laughter_ogg"), -2)
            a0 = c.get("trecho", 0.0)
            por(efeitos, reamostrar(trecho(x, a0, a0 + c.get("dur", 2.0) * c.get("tom", 1.0), 0.25), c.get("tom", 1.0)),
                tempo_de(c, P), c.get("g", -12))
        elif kind == "saco":
            por(efeitos, amassado(c.get("dur", 0.7), int(tempo_de(c, P))), tempo_de(c, P), c.get("g", -10))
        elif kind == "arquivo":  # any cached PD/CC0 sound: "nome", "trecho" (start in the file), "dur", "tom", "g"
            x = norm(ler(c["nome"]), -2)
            a0, tom = c.get("trecho", 0.0), c.get("tom", 1.0)
            por(efeitos, reamostrar(trecho(x, a0, a0 + c.get("dur", 2.0) * tom, 0.2), tom), tempo_de(c, P), c.get("g", -12))
        else:
            raise SystemExit(f"som desconhecido no plano: {kind}")

    # camera: whoosh into every whip/fly, impact on story cuts and kicks, a lighter swish on montage cuts
    for k in keys[1:]:
        if k["move"] in ("whip", "fly"):
            por(efeitos, sfx.som("whoosh"), k["t"] - k.get("dur", 0.3), -6 if k["move"] == "fly" else -3)
        elif k["move"] == "cut":
            if k.get("tag") == "montagem":
                por(efeitos, sfx.som("whoosh"), k["t"] - 0.18, -7)
            elif k.get("tag") in ("insert", "final"):
                por(efeitos, sfx.som("impacto"), k["t"], 0)
                por(efeitos, guincho(0.6, int(k["t"] * 10)), k["t"], -6)
            elif k.get("tag") != "volta":
                por(efeitos, sfx.som("impacto"), k["t"], 3)
    for t, amp in kicks:
        por(efeitos, sfx.som("impacto"), t, -6 + amp / 10)

    # riser from the switch lever into the silence (cut dead), then the bed slams back after it
    if plano.get("riser_de") and silencios:
        a, b = resolver(plano["riser_de"], P), silencios[0][0]
        por(efeitos, riser(b - a), a, -4)
        por(efeitos, sfx.som("impacto"), silencios[0][1], 2)

    # countdown: a real tick every second, beeps on the last three
    tique = grãos(norm(ler("clock_ticking_ogg")), 1, 0.12)[0]
    for s in range(10):
        t = cont + s
        if t < fim_som:
            por(efeitos, tique, t, -2)
            if s >= 7:
                por(efeitos, sfx.som("ding"), t, -5)
    # the freeze: a hit + a deafening whistle that cuts to silence
    if congela < DUR:
        por(efeitos, sfx.som("impacto"), congela, 5)
        a = congela - 0.6
        por(efeitos, loop(apito, int((fim_som - a) * SR) + 10), a, 3)
        por(efeitos, norm(trecho(ler("airchime_k5la_ogg"), 0.6, 0.6 + fim_som - a, 0.03), -1), a, -4)

    mudo = mascara(silencios + fim)
    efeitos *= mudo

    # mix: voice + effects (effects never above the voice), then music bed + loudness in mixar_audio
    voz = ve.ler_wav(src / "voz.wav").astype(np.float32)[:N]
    mix[: len(voz)] += voz
    fala = np.convolve(np.abs(mix), np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
    duck = np.where(fala > 0.02, db(-5), 1.0).astype(np.float32)
    duck = np.convolve(duck, np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same").astype(np.float32)
    mix += efeitos * duck * db(-2)
    pre = ve.salvar_wav(pub / "voz_sfx.wav", np.clip(mix, -1, 1))
    final = va.mixar_audio(pre, pub / "audio.wav", DUR, _bgm_mudo(silencios + fim))
    if fim:
        _zerar_final(final, fim_som)
    usados = [json.loads((sons.CACHE / f"{k}.json").read_text(encoding="utf-8")) for k in sorted(_usados)]
    sons.creditos(usados, pub / "creditos_sons.txt")

    ev = {"keys": keys, "kicks": kicks, "puxadas": puxadas, "solta": solta, "batidas": batidas, "latidos": latidos,
          "contagem": cont, "duracao": DUR, "titulo_ate": plano.get("titulo_ate", 1.7), "congela": congela,
          "fim_som": fim_som, "silencios": silencios, "faiscas": faiscas, "trem": trem,
          "respiros": tl.get("respiros", [])}
    (src / "eventos.json").write_text(json.dumps(ev, ensure_ascii=False), encoding="utf-8")
    print(f"ok: {final} | {len(keys)} chaves, {len(batidas)} batidas, {len(latidos)} latidos, silêncio {silencios}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
