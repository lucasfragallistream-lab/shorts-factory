"""Staging of one miniseries scene: where each character stands over time, their arm pose, face and mouth.

Pure logic (no drawing), consumed by novela_hf.py. Times are seconds from the start of the scene.

- Speakers always gesture: an explicit `gesto`, the pose implied by the `acao`, or a pose picked from the
  emotion (long lines switch to a second gesture halfway).
- Actions move people: aproxima (walk up to the target), empurra (rush in, the target staggers back),
  abraca (both meet in the middle and hug), entra / sai (walk in from / out to the nearest edge).
- Listeners react: a target of anger, mockery or pointing goes "chocado" with a hand on the chest.
- One-arm poses use the figure's viewer-right arm; when the target is on the left the image is mirrored
  (pose key suffix "_e").
"""
from __future__ import annotations

from dataclasses import dataclass, field

L = 1080
FORA = 300  # px beyond the frame edge for off-screen positions
ANDAR = 0.7
AUTO = {
    "raiva": ("aponta", "bracos_cima"),
    "deboche": ("maos_cintura", "aponta"),
    "chorando": ("maos_rosto", "mao_peito"),
    "triste": ("mao_peito", "parado"),
    "choque": ("bracos_cima", "mao_peito"),
    "medo": ("mao_peito", "estende"),
    "esperanca": ("estende", "mao_peito"),
    "neutra": ("estende", "parado"),
}
ASSIMETRICAS = {"aponta", "estende", "mao_peito"}


@dataclass
class Movimento:
    t: float
    dur: float
    x0: float
    x1: float


@dataclass
class Ator:
    id: str
    casa: float  # home x (where the images are placed)
    x_ini: float
    movs: list[Movimento] = field(default_factory=list)
    expr: list[tuple[float, str]] = field(default_factory=list)
    boca: list[tuple[float, str]] = field(default_factory=list)
    pose: list[tuple[float, str, str | None]] = field(default_factory=list)  # (t, pose, aimed-at id)
    pulos: list[float] = field(default_factory=list)  # small hop when a line starts

    def x(self, t: float) -> float:
        x = self.x_ini
        for m in self.movs:
            if t < m.t:
                break
            if t < m.t + m.dur:
                k = (t - m.t) / m.dur
                return m.x0 + (m.x1 - m.x0) * k
            x = m.x1
        return x

    def mover(self, t: float, dur: float, x1: float):
        self.movs.append(Movimento(round(t, 3), dur, round(self.x(t), 1), round(x1, 1)))
        self.movs.sort(key=lambda m: m.t)


def _limitar(x: float) -> float:
    return max(150.0, min(L - 150.0, x))


def _passo(ev: list, t: float, padrao):
    v = padrao
    for e in ev:
        if e[0] <= t + 1e-6:
            v = e[1:] if len(e) > 2 else e[1]
        else:
            break
    return v


def encenar(falas: list[dict], presentes: list[str], xs: list[float], papeis: dict[str, str], protagonista: str,
            expr_de: dict[str, str], ouvindo: dict[str, str], chegadas: dict[str, float] | None = None
            ) -> dict[str, Ator]:
    """`falas`: timeline lines of this scene with times relative to the scene start."""
    chegadas = chegadas or {}
    atores: dict[str, Ator] = {}
    for mid, x in zip(presentes, xs):
        entra = any(f["quem"] == mid and f.get("acao") == "entra" for f in falas) or mid in chegadas
        x_ini = (-FORA if x < L / 2 else L + FORA) if entra else x
        if mid in chegadas:
            x_ini = L + FORA
        a = Ator(mid, x, x_ini)
        a.expr.append((0.0, ouvindo[papeis[mid]]))
        a.boca.append((0.0, "fechada"))
        a.pose.append((0.0, "parado", None))
        if mid in chegadas:
            a.mover(chegadas[mid], 0.8, x)
        atores[mid] = a

    for f in falas:
        a0, b0 = f["inicio"], f["fim"]
        q, alvo = f["quem"], f.get("alvo")
        acao, emocao = f.get("acao"), f["emocao"]
        if q in atores:
            at = atores[q]
            tgt = atores.get(alvo) if alvo else None
            if acao == "entra":
                at.mover(max(0.0, a0 - 0.5), 0.8, at.casa)
            elif acao in ("aproxima", "empurra", "abraca") and tgt is not None:
                tx, sx = tgt.x(a0), at.x(a0)
                lado = 1 if sx >= tx else -1
                if acao == "aproxima":
                    at.mover(a0, ANDAR, _limitar(tx + lado * 300))
                elif acao == "empurra":
                    at.mover(max(0.0, a0 - 0.18), 0.18, sx + lado * 45)  # anticipation: wind up before the push
                    at.mover(a0, 0.3, _limitar(tx + lado * 230))
                    tgt.mover(a0 + 0.3, 0.35, max(90.0, min(L - 90.0, tx - lado * 210)))  # staggers back
                    tgt.expr.append((a0 + 0.3, "chocado"))
                    tgt.pose.append((a0 + 0.3, "mao_peito", q))
                    tgt.pose.append((b0 + 0.3, "parado", None))
                else:  # abraca
                    meio = (sx + tx) / 2
                    at.mover(a0, ANDAR, _limitar(meio + lado * 115))
                    tgt.mover(a0, ANDAR, _limitar(meio - lado * 115))
                    tgt.pose.append((a0 + 0.35, "abraca", q))
                    tgt.pose.append((b0 + 0.8, "parado", None))
            elif acao == "sai":
                at.mover(b0, 0.9, -FORA if at.x(b0) < L / 2 else L + FORA)
            at.expr.append((a0, expr_de[emocao]))
            for w in f["palavras"]:
                wa = w["inicio"]
                wb = max(wa + 0.07, w["fim"] - 0.05)
                at.boca += [(wa, "aberta"), (wb, "fechada")]
            at.boca.append((b0, "fechada"))
            if acao == "empurra":
                gestos = [("estende", a0 + 0.05)]
            elif acao == "abraca":
                gestos = [("abraca", a0 + 0.35)]
            elif f.get("gesto"):
                gestos = [(f["gesto"], a0 + 0.1)]
            else:
                g1, g2 = AUTO.get(emocao, ("estende", "parado"))
                gestos = [(g1, a0 + 0.1)] + ([(g2, (a0 + b0) / 2)] if b0 - a0 > 2.4 else [])
            for g, t in gestos:
                at.pose.append((t, g, alvo))
            at.pose.append((b0 + (0.8 if acao == "abraca" else 0.15), "parado", None))
            if acao is None:
                at.pulos.append(a0)
        # listener reactions
        if q != "narrador" and acao not in ("empurra", "abraca"):
            ataque = emocao in ("raiva", "deboche") or f.get("gesto") == "aponta"
            vitima = alvo if alvo in atores else (protagonista if protagonista in atores and q != protagonista
                                                  and papeis.get(q) in ("vilao", "vila") else None)
            if ataque and vitima and vitima != q:
                v = atores[vitima]
                v.expr.append((a0 + 0.3, "chocado"))
                v.pose.append((a0 + 0.3, "mao_peito", q))
                v.pose.append((b0 + 0.2, "parado", None))
    for a in atores.values():
        a.expr.sort(key=lambda e: e[0])
        a.boca.sort(key=lambda e: e[0])
        a.pose.sort(key=lambda e: e[0])
    return atores


def _mirar(at: Ator, alvo: str | None, atores: dict[str, Ator], t: float) -> bool:
    """True when the aimed-at person (or the nearest one) stands to the left -> mirror the image."""
    x = at.x(t)
    if alvo and alvo in atores:
        ax = atores[alvo].x(t)
    else:
        outros = [o.x(t) for o in atores.values() if o is not at and -FORA / 2 < o.x(t) < L + FORA / 2]
        ax = min(outros, key=lambda v: abs(v - x)) if outros else L / 2
    return ax < x


def estados(at: Ator, atores: dict[str, Ator], fim: float) -> list[tuple[float, str, str, str]]:
    """Merged (t, expr, boca, pose_key) steps; one event per change."""
    tempos = sorted({t for t, *_ in at.expr + at.boca + at.pose if 0 <= t < fim} | {0.0})
    out: list[tuple[float, str, str, str]] = []
    for t in tempos:
        e = _passo(at.expr, t, "feliz")
        b = _passo(at.boca, t, "fechada")
        pose, alvo = _passo(at.pose, t, ("parado", None))
        pk = pose + ("_e" if pose in ASSIMETRICAS and _mirar(at, alvo, atores, t + 0.2) else "")
        if not out or out[-1][1:] != (e, b, pk):
            out.append((round(t, 3), e, b, pk))
    return out
