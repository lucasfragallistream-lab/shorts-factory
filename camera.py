"""Camera grammar for the miniseries (pure logic; novela_hf.py turns it into GSAP tweens).

Rules measured from viral animated shorts (mromidev/claude-animated-shorts, STYLE_BIBLE):
- glide between speakers (ease-out burst, 0.6-1.2 s) instead of cutting; hard cut only on big jumps
- the camera never holds still: every hold creeps in (0.25 %/frame, 0.5 % on punch lines, capped)
- the camera follows whatever moves (a person walking, pushing, entering; the car arriving)
- dutch roll ~4.5 deg on anger / shock / fear lines
- impact kick: shake that flips sign every frame and dies in 7 frames
Times are seconds from the start of the scene; framings are dicts {cx, cy, z} in stage pixels.
"""
from __future__ import annotations

import math

L, A = 1080, 1920
GLIDE_MIN, GLIDE_MAX = 0.6, 1.0
EASE = "power2.inOut"  # soft start, velocity peak near the middle, settle (kit: peak ~40 %)
SALTO_CORTE = 1500.0  # screen-distance above which we hard cut instead of gliding
CREEP, CREEP_PUNCH, CREEP_MAX = 0.0025, 0.005, 1.08
ROLL = 4.5
ROLL_ESCALA = 1.14  # extra zoom while rolled so the corners never show
PASSO = 0.1  # sampling step while following a moving subject
DRAMA = ("raiva", "choque", "medo")


def pos(cx: float, cy: float, z: float) -> tuple[float, float, float]:
    """Camera transform (x, y, scale) with origin at 0,0 that centers (cx, cy) without showing outside the stage."""
    x = min(0.0, max(L - L * z, L / 2 - cx * z))
    y = min(0.0, max(A - A * z, A / 2 - cy * z))
    return round(x, 1), round(y, 1), round(z, 4)


def _dist(a: dict, b: dict) -> float:
    z = max(a["z"], b["z"])
    return math.hypot((a["cx"] - b["cx"]) * z, (a["cy"] - b["cy"]) * z) + abs(a["z"] - b["z"]) * 700


def _key(t: float, d: float, f: dict, ease: str) -> list:
    x, y, s = pos(f["cx"], f["cy"], f["z"])
    return [round(max(0.0, t), 3), round(max(0.0, d), 3), x, y, s, ease]


def _palavra_chave(f: dict) -> float:
    """Time of the word the camera should arrive on: first word of the highlight, else the line's first word."""
    pals = f.get("palavras") or []
    if f.get("destaque") and pals:
        alvo = f["destaque"].split()[0].lower().strip(".,!?")
        for w in pals:
            if w["texto"].lower().strip(".,!?") == alvo:
                return w["inicio"]
    return pals[0]["inicio"] if pals else f["inicio"]


def planejar(falas: list[dict], enquadrar, janelas: list[tuple[float, float, object]], dur: float) -> dict:
    """falas: scene lines (relative times) with "inicio", "fim", "emocao", "destaque", "acao".
    enquadrar(f) -> framing at the moment the line lands.
    janelas: (t0, t1, f(t) -> framing) spans where the camera follows something that moves.
    Returns {"cam": [[t, d, x, y, s, ease]], "roll": [[t, rot, scale]], "kick": [[t, amp]]}.
    """
    cam: list[list] = []
    roll: list[list] = []
    kick: list[list] = []
    alvos: list[tuple[float, float, dict, bool]] = []  # (glide start, land, framing, punch)
    prev = None
    for i, f in enumerate(falas):
        fr = enquadrar(f)
        punch = bool(f.get("destaque")) or f.get("acao") == "empurra"
        if prev is None:
            ini, d = 0.0, 0.0
        else:
            dist = _dist(prev, fr)
            d = 0.0 if dist > SALTO_CORTE else min(GLIDE_MAX, max(GLIDE_MIN, 0.6 + dist / 2500))
            pousa = _palavra_chave(f)  # the move lands ON the key word
            ini = max(alvos[-1][1] + 0.05, pousa - d)
            if d == 0.0:
                ini = max(alvos[-1][1] + 0.05, f["inicio"] - 0.03)
        alvos.append((ini, ini + d, fr, punch))
        prev = fr
        rot = (ROLL if i % 2 else -ROLL) if f.get("emocao") in DRAMA else 0.0
        roll.append([round(ini, 3), rot, ROLL_ESCALA if rot else 1.0])
        if punch:
            kick.append([round(f["inicio"] + (0.3 if f.get("acao") == "empurra" else 0.08), 3), 22.0])
    # line keys: glide (or cut) then creep until the next glide starts
    for k, (ini, land, fr, punch) in enumerate(alvos):
        fim = alvos[k + 1][0] if k + 1 < len(alvos) else dur
        cam.append(_key(ini, land - ini, fr, EASE if land > ini else "none"))
        span = max(0.0, fim - land)
        if span > 0.05:
            fator = min(CREEP_MAX, 1 + (CREEP_PUNCH if punch else CREEP) * span * 30)
            cam.append(_key(land, span, {**fr, "z": fr["z"] * fator}, "none"))
    # follow windows override what was planned inside them, then glide back to the current line framing
    for t0, t1, segue in sorted(janelas, key=lambda j: j[0]):
        t1 = min(t1, dur)
        if t1 - t0 < 0.2:
            continue
        cam = [c for c in cam if not (t0 <= c[0] < t1 + GLIDE_MIN)]
        for c in cam:  # cut short the key that spans the window start
            if c[0] < t0 < c[0] + c[1]:
                c[1] = round(t0 - c[0], 3)
        n = max(1, round((t1 - t0) / PASSO))
        for j in range(n):
            ta = t0 + (t1 - t0) * j / n
            cam.append(_key(ta, (t1 - t0) / n, segue(ta + (t1 - t0) / n), "none" if j else "power2.out"))
        atual = next((a for a in reversed(alvos) if a[0] <= t1), alvos[0] if alvos else None)
        if atual is not None:
            prox = next((c[0] for c in sorted(cam, key=lambda c: c[0]) if c[0] >= t1), dur)
            cam.append(_key(t1, GLIDE_MIN, atual[2], EASE))
            if prox - (t1 + GLIDE_MIN) > 0.05:
                fr = atual[2]
                cam.append(_key(t1 + GLIDE_MIN, prox - t1 - GLIDE_MIN, {**fr, "z": fr["z"] * 1.04}, "none"))
    cam.sort(key=lambda c: c[0])
    return {"cam": cam, "roll": roll, "kick": kick}


def parado_max(cam: list[list], dur: float, fps: int = 30) -> float:
    """Longest span (s) in which no camera key is active, i.e. the picture would freeze."""
    fim, maior = 0.0, 0.0
    for t, d, *_ in sorted(cam, key=lambda c: c[0]):
        maior = max(maior, t - fim)
        fim = max(fim, t + d)
    return max(maior, dur - fim)
