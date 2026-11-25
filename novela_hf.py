"""Builds a HyperFrames project (HTML -> MP4) for one miniseries episode.

Layout of the generated project (motion/<nome>/):
  index.html                 root, 1080x1920, `duracao` s: scene hosts, captions host, hook host, end host, audio
  compositions/cenaN.html    one per scene: background, cast (one <img> per expression/mouth), props, rain,
                             big highlight words, name chips; a camera wrapper cuts to close/medium/wide per line
  compositions/legendas.html word-by-word captions (groups of up to 3 words, active word in yellow)
  compositions/gancho.html   frame 0: extreme close-up of the protagonist's face under the giant title
  compositions/fim.html      "CONTINUA..." end card with the comment question
  assets/                    PNGs rendered here with Pillow (figure_renderer, cenarios) and audio.wav
"""
from __future__ import annotations

import html
import json
import math
import re
import shutil
from pathlib import Path

import camera
import cenarios
import encenacao
import figure_renderer as fr
from novela_schema import Episodio

L, A = 1080, 1920
H_FIG = 1100  # figure canvas height (1x); adults are ~1030 px tall
AMARELO = "#FFD60A"
VERMELHO = "#E8463E"

EXPR = {"neutra": "feliz", "deboche": "feliz", "esperanca": "feliz", "triste": "triste", "chorando": "triste",
        "raiva": "raiva", "choque": "chocado", "medo": "preocupado"}
OUVINDO = {"protagonista": "preocupado", "vilao": "raiva", "vila": "feliz", "aliado": "feliz", "misterio": "feliz"}


def _esc(t: str) -> str:
    return html.escape(t, quote=True)


def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


# --- assets ------------------------------------------------------------------------------
def _posicoes(n: int) -> list[float]:
    if n == 1:
        return [L * 0.5]
    margem = 220 if n == 2 else (170 if n == 3 else 140)
    return [margem + (L - 2 * margem) * i / (n - 1) for i in range(n)]


def _escala(n: int) -> float:
    """Smaller figures when the scene is crowded, so four people fit side by side."""
    return {1: 1.0, 2: 1.0, 3: 0.9}.get(n, 0.8)


def _salvar_figura(ep: Episodio, mid: str, expr: str, boca: str, pk: str, pasta: Path, altura: int = H_FIG) -> str:
    """pk = pose key: pose name, "_e" suffix = mirrored (one-arm gesture aimed to the left)."""
    from PIL import Image

    nome = f"p_{mid}_{expr}_{boca}_{pk}_{altura}.png"
    destino = pasta / nome
    if not destino.exists():
        pose = pk.removesuffix("_e")
        img = fr.renderizar(ep.membro(mid).personagem, altura * 2, expr, boca, pose=pose, margem=fr.MARGEM_POSE)
        if pk.endswith("_e"):
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        img.save(destino)
    return f"assets/{nome}"


def _gancho_assets(ep: Episodio, pasta: Path) -> tuple[str, str]:
    from montagem import _rosto_close, _titulo_gigante

    prot = ep.protagonista().personagem.model_copy(update={"expressao": "triste"})
    rosto = _rosto_close(prot.model_dump_json())
    # the close-up helper renders "chocado"; for drama the protagonist cries
    p2 = fr.renderizar(prot, 2600, "triste")
    g = fr._Geo(prot)
    k = 2600 / fr.ALT_U
    cx, cy, lado = fr.CX * k, (g.olho_y + g.d * 0.08) * k, g.d * 1.3 * k
    rosto = p2.crop((round(cx - lado / 2), round(cy - lado / 2), round(cx + lado / 2), round(cy + lado / 2)))
    rosto.resize((1150, 1150)).save(pasta / "gancho_rosto.png")
    _titulo_gigante(ep.titulo).save(pasta / "gancho_titulo.png")
    return "assets/gancho_rosto.png", "assets/gancho_titulo.png"


# --- per-scene composition ---------------------------------------------------------------
def _enquadrar(f: dict, presentes: dict, protagonista: str) -> dict:
    alvo = f["quem"] if f["quem"] in presentes else (protagonista if protagonista in presentes
                                                      else next(iter(presentes)))
    x, topo, altura = presentes[alvo]
    if f["enquadramento"] == "geral" or (f["quem"] == "narrador" and f["enquadramento"] != "close"):
        return {"cx": L / 2, "cy": 1060, "z": 1.0}
    if f["enquadramento"] == "close":
        return {"cx": x, "cy": topo + altura * 0.14 + 300 / 2.35, "z": 2.35}  # face sits ~300 px above center
    return {"cx": x, "cy": topo + altura * 0.36, "z": 1.5}


def _cena_html(ep: Episodio, ci: int, tl: dict, assets: Path) -> tuple[str, float]:
    cena = ep.cenas[ci]
    c_tl = tl["cenas"][ci]
    t0 = c_tl["inicio"]
    dur = (tl["duracao"] if ci == len(ep.cenas) - 1 else c_tl["fim"]) - t0
    cid = f"cena{ci}"
    cenarios.fundo(cena.cenario, cena.chuva).save(assets / f"bg_{ci}.png")
    xs = _posicoes(len(cena.presentes))
    hfig = round(H_FIG * _escala(len(cena.presentes)))
    canvas_w = hfig * (fr.LARG_U + 2 * fr.MARGEM_POSE) / fr.ALT_U
    presentes, imgs, estados = {}, [], []
    falas = [f for f in tl["falas"] if f["cena"] == ci]
    carro_chega = None
    if "carro_luxo" in cena.objetos:
        _pal = [w for f in falas for w in f["palavras"] if re.match(r"carro", w["texto"].lower())]
        carro_chega = (_pal[0]["inicio"] - t0) if _pal else None  # no mention: the car is already parked
    rel = [{**f, "inicio": f["inicio"] - t0, "fim": f["fim"] - t0,
            "palavras": [{**w, "inicio": w["inicio"] - t0, "fim": w["fim"] - t0} for w in f["palavras"]]}
           for f in falas]
    papeis = {mid: ep.membro(mid).papel for mid in cena.presentes}
    chegadas = ({mid: carro_chega + 1.0 for mid in cena.presentes if papeis[mid] == "misterio"}
                if carro_chega is not None else {})
    atores = encenacao.encenar(rel, cena.presentes, xs, papeis, ep.protagonista().id, EXPR, OUVINDO, chegadas)
    movs, inis, pulos = [], [], []
    for mid, x in zip(cena.presentes, xs):
        m = ep.membro(mid)
        at = atores[mid]
        topo_canvas = cenarios.CHAO_Y - hfig * fr.CHAO_U / fr.ALT_U
        topo_cabeca = topo_canvas + hfig * fr.topo(m.personagem)
        presentes[mid] = (x, topo_cabeca, cenarios.CHAO_Y - topo_cabeca)
        ev = encenacao.estados(at, atores, dur)
        imgs.append(f'<div id="{cid}-quem-{mid}" class="quem">')
        for expr, boca, pk in sorted({e[1:] for e in ev}):
            src = _salvar_figura(ep, mid, expr, boca, pk, assets, hfig)
            iid = f"{cid}-{mid}-{expr}-{boca}-{pk}"
            imgs.append(f'<img id="{iid}" class="pers {cid}-{mid}" src="{src}" alt="" style="left:{x - canvas_w / 2:.1f}px;'
                        f'top:{topo_canvas:.1f}px;width:{canvas_w:.1f}px;height:{hfig}px">')
        imgs.append("</div>")
        estados.append({"m": mid, "ev": [[round(t, 3), e, b, pk] for t, e, b, pk in ev]})
        if at.x_ini != at.casa:
            inis.append([mid, round(at.x_ini - at.casa, 1)])
        movs += [[mid, mv.t, mv.dur, round(mv.x0 - at.casa, 1), round(mv.x1 - at.casa, 1)] for mv in at.movs]
        pulos += [[mid, round(t, 3)] for t in at.pulos]
    props = []
    if "malas" in cena.objetos:
        cenarios.malas().save(assets / "malas.png")
        props.append(f'<img id="{cid}-malas" class="prop" src="assets/malas.png" alt="" '
                     f'style="left:30px;top:{cenarios.CHAO_Y - 300}px;width:420px;height:300px">')
    carro_t = None
    if "carro_luxo" in cena.objetos:
        cenarios.carro().save(assets / "carro.png")
        props.append(f'<img id="{cid}-carro" class="prop" src="assets/carro.png" alt="" '
                     f'style="left:60px;top:{cenarios.CHAO_Y + 20}px;width:1000px;height:380px">')
        palavras = [w for f in falas for w in f["palavras"] if re.match(r"carro", w["texto"].lower())]
        carro_t = (palavras[0]["inicio"] - t0) if palavras else None
    protagonista = ep.protagonista().id

    def enquadrar(f: dict) -> dict:
        ta = f["inicio"] + (0.8 if f.get("acao") in ("aproxima", "empurra", "abraca", "entra") else 0.3)
        agora = {mid: (atores[mid].x(ta),) + presentes[mid][1:] for mid in presentes}
        e = _enquadrar(f, agora, protagonista)
        if f.get("acao") in ("aproxima", "empurra", "abraca") and f.get("alvo") in agora:
            par = (agora[f["quem"]][0] + agora[f["alvo"]][0]) / 2
            e = {"cx": par, "cy": agora[f["quem"]][1] + agora[f["quem"]][2] * 0.42, "z": 1.3}
        return e

    def _segue(mid: str):
        _, topo, alt = presentes[mid]
        return lambda t: {"cx": atores[mid].x(t), "cy": topo + alt * 0.42, "z": 1.25}

    janelas = [(mv.t, mv.t + mv.dur + 0.1, _segue(mid)) for mid in presentes for mv in atores[mid].movs
               if mv.dur >= 0.3 and 0 <= mv.t < dur]
    if carro_t is not None:
        janelas.append((carro_t, carro_t + 1.0, lambda t: {
            "cx": 560 + 1200 * (1 - min(1.0, (t - carro_t) / 1.0)) ** 3, "cy": cenarios.CHAO_Y + 60, "z": 1.1}))
    plano = camera.planejar(rel, enquadrar, janelas, dur)
    fx = []
    cenarios.estrela().save(assets / "fx_estrela.png")
    cenarios.poeira().save(assets / "fx_poeira.png")
    for f in rel:
        if f.get("acao") == "empurra" and f.get("alvo") in presentes:
            ta = f["inicio"] + 0.35
            _, topo, alt = presentes[f["alvo"]]
            fx.append(("estrela", ta, atores[f["alvo"]].x(ta), topo + alt * 0.3))
    for mid in presentes:
        for mv in atores[mid].movs:
            if mv.dur >= 0.3 and -100 < mv.x1 < L + 100:
                fx.append(("poeira", mv.t + mv.dur, mv.x1, cenarios.CHAO_Y - 20))
    fx_html, fx_dados = [], []
    for k, (tipo, t, x, y) in enumerate(fx):
        w = 360 if tipo == "estrela" else 300
        fx_html.append(f'<img id="{cid}-fx{k}" class="fx" src="assets/fx_{tipo}.png" alt="" '
                       f'style="left:{x - w / 2:.0f}px;top:{y - w / 2:.0f}px;width:{w}px;height:{w}px">')
        fx_dados.append([f"#{cid}-fx{k}", round(t, 3), tipo])
    overlays = []
    vistos = set()
    for k, f in enumerate(falas):
        a = f["inicio"] - t0
        if f["destaque"]:
            overlays.append(f'<div id="{cid}-dest{k}" class="clip destaque" data-start="{a:.3f}" '
                            f'data-duration="{min(1.8, f["fim"] - f["inicio"] + 0.2):.3f}" data-track-index="1" '
                            f'data-layout-allow-overflow><span id="{cid}-dest{k}-t">{_esc(f["destaque"].upper())}</span></div>')
        if f["quem"] != "narrador" and f["quem"] not in vistos:
            vistos.add(f["quem"])
            m = ep.membro(f["quem"])
            overlays.append(f'<div id="{cid}-nome{k}" class="clip nome" data-start="{a:.3f}" data-duration="1.6" '
                            f'data-track-index="2"><span id="{cid}-nome{k}-t">{_esc(m.nome.upper())}</span></div>')
    chuva = ""
    if cena.chuva:
        import random

        rnd = random.Random(ci + 3)
        gotas = "".join(
            f'<i style="left:{rnd.uniform(0, L):.0f}px;top:{rnd.uniform(0, A * 2):.0f}px;'
            f'height:{rnd.uniform(50, 110):.0f}px"></i>' for _ in range(140))
        chuva = f'<div id="{cid}-chuva" class="chuva" data-layout-ignore>{gotas}</div>'
    slams = [[f"#{cid}-dest{k}-t", round(f["inicio"] - t0, 3)] for k, f in enumerate(falas) if f["destaque"]]
    nomes = [[f"#{cid}-nome{k}-t", round(f["inicio"] - t0, 3)] for k, f in enumerate(falas)
             if f'id="{cid}-nome{k}"' in "".join(overlays)]
    dados = {"cam": plano["cam"], "roll": plano["roll"], "kick": plano["kick"], "fx": fx_dados,
             "whipIn": ci > 0, "whipOut": ci < len(ep.cenas) - 1, "estados": estados, "dur": round(dur, 3), "carro": carro_t,
             "chuva": cena.chuva, "slams": slams, "nomes": nomes, "movs": movs, "inis": inis, "pulos": pulos}
    doc = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; background: #fafafa; }}
    #{cid}-shake, #{cid}-cam {{ position: absolute; left: 0; top: 0; width: {L}px; height: {A}px; }}
    .bg {{ position: absolute; left: 0; top: 0; width: {L}px; height: {A}px; }}
    .pers, .prop {{ position: absolute; }}
    .quem {{ position: absolute; left: 0; top: 0; width: {L}px; height: {A}px; }}
    .pers {{ opacity: 0; }}
    .fx {{ position: absolute; opacity: 0; z-index: 5; }}
    .destaque {{ position: absolute; left: 0; width: {L}px; top: 360px; text-align: center; z-index: 20; }}
    .destaque span {{ display: inline-block; font-family: 'Archivo Black'; font-size: 112px; line-height: 1.02;
      color: {AMARELO}; -webkit-text-stroke: 14px #26282f; paint-order: stroke fill; padding: 0 60px;
      text-shadow: 0 10px 0 #26282f; }}
    .nome {{ position: absolute; left: 130px; top: 300px; z-index: 21; }}
    .nome span {{ display: inline-block; font-family: 'Archivo Black'; font-size: 40px; color: #fff;
      background: {VERMELHO}; border: 6px solid #26282f; border-radius: 18px; padding: 8px 26px; }}
    .chuva {{ position: absolute; left: 0; top: -{A}px; width: {L}px; height: {A * 2}px; z-index: 10;
      pointer-events: none; }}
    .chuva i {{ position: absolute; width: 4px; border-radius: 3px; background: rgba(200, 220, 255, 0.55); }}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="{L}" data-height="{A}">
    <div id="{cid}-shake" data-layout-allow-overflow>
      <div id="{cid}-cam" data-layout-allow-overflow>
        <img id="{cid}-bg" class="bg" src="assets/bg_{ci}.png" alt="">
        {''.join(props)}
        {''.join(imgs)}
        {''.join(fx_html)}
      </div>
    </div>
    {chuva}
    {''.join(overlays)}
  </div>
  <script>
    (function () {{
      const D = {json.dumps(dados, ensure_ascii=False)};
      const tl = gsap.timeline({{ paused: true }});
      const cam = "#{cid}-cam", shake = "#{cid}-shake";
      tl.set(cam, {{ transformOrigin: "0 0" }}, 0);
      tl.set(shake, {{ transformOrigin: "50% 50%" }}, 0);
      D.cam.forEach(function (c) {{
        const v = {{ x: c[2], y: c[3], scale: c[4] }};
        if (c[1] <= 0) {{ tl.set(cam, v, c[0]); }}
        else {{ tl.to(cam, Object.assign(v, {{ duration: c[1], ease: c[5] }}), c[0]); }}
      }});
      D.roll.forEach(function (r) {{
        tl.to(shake, {{ rotation: r[1], scale: r[2], duration: 0.45, ease: "power2.out" }}, r[0]);
      }});
      D.kick.forEach(function (k) {{  // impact kick: flips sign every frame, dies in 7 frames
        const kf = [];
        for (let i = 0; i < 7; i++) {{ const a = k[1] * (1 - i / 7) * (i % 2 ? 1 : -1); kf.push({{ x: a, y: -a * 0.5 }}); }}
        kf.push({{ x: 0, y: 0 }});
        tl.to(shake, {{ keyframes: kf, duration: 8 / 30, ease: "none" }}, k[0]);
      }});
      if (D.whipIn) {{
        tl.fromTo(shake, {{ x: 560, filter: "blur(18px)" }}, {{ x: 0, filter: "blur(0px)", duration: 0.26,
          ease: "power3.out" }}, 0);
      }}
      if (D.whipOut) {{
        tl.to(shake, {{ x: -560, filter: "blur(18px)", duration: 0.22, ease: "power3.in" }}, D.dur - 0.22);
      }}
      D.fx.forEach(function (f) {{
        if (f[2] === "estrela") {{
          tl.fromTo(f[0], {{ scale: 0.2, opacity: 1, rotation: -20 }}, {{ scale: 1.25, rotation: 10, duration: 0.18,
            ease: "back.out(2)", immediateRender: false }}, f[1]);
          tl.to(f[0], {{ opacity: 0, duration: 0.2 }}, f[1] + 0.25);
        }} else {{
          tl.fromTo(f[0], {{ scale: 0.5, opacity: 0.9 }}, {{ scale: 1.4, opacity: 0, duration: 0.45, ease: "power2.out",
            immediateRender: false }}, f[1]);
        }}
      }});
      D.estados.forEach(function (s) {{
        const todos = ".{cid}-" + s.m;
        s.ev.forEach(function (e) {{
          tl.set(todos, {{ opacity: 0 }}, e[0]);
          tl.set("#{cid}-" + s.m + "-" + e[1] + "-" + e[2] + "-" + e[3], {{ opacity: 1 }}, e[0]);
        }});
        // breathing: tiny stretch from the feet, all of this person's images together
        tl.to(todos, {{ scaleY: 1.012, transformOrigin: "50% 92%", duration: 1.3, ease: "sine.inOut", yoyo: true,
          repeat: Math.max(1, Math.ceil(D.dur / 1.3)) }}, 0);
      }});
      D.inis.forEach(function (m) {{ tl.set("#{cid}-quem-" + m[0], {{ x: m[1] }}, 0); }});
      D.movs.forEach(function (m) {{
        const q = "#{cid}-quem-" + m[0];
        tl.fromTo(q, {{ x: m[3] }}, {{ x: m[4], duration: m[2], ease: "power1.inOut", immediateRender: false }}, m[1]);
        const passos = Math.max(2, Math.round(m[2] / 0.18));
        const kf = [];
        for (let k = 0; k < passos; k++) {{ kf.push({{ y: k % 2 ? 0 : -16 }}); }}
        kf.push({{ y: 0 }});
        tl.fromTo(q, {{ y: 0 }}, {{ keyframes: kf, duration: m[2], ease: "none", immediateRender: false }}, m[1]);
      }});
      D.pulos.forEach(function (p) {{
        tl.fromTo("#{cid}-quem-" + p[0], {{ y: 0 }}, {{ keyframes: [{{ y: -20 }}, {{ y: 0 }}], duration: 0.28,
          ease: "power1.out", immediateRender: false }}, p[1]);
      }});
      D.slams.forEach(function (s) {{
        tl.fromTo(s[0], {{ scale: 1.9, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.16, ease: "power3.out" }}, s[1]);
      }});
      D.nomes.forEach(function (s) {{
        tl.fromTo(s[0], {{ x: -320 }}, {{ x: 0, duration: 0.25, ease: "power3.out" }}, s[1]);
      }});
      if (D.carro !== null) {{
        tl.fromTo("#{cid}-carro", {{ x: 1200 }}, {{ x: 0, duration: 1.0, ease: "power3.out" }}, D.carro);
      }}
      if (D.chuva) {{
        tl.fromTo("#{cid}-chuva", {{ y: 0 }}, {{ y: {A}, duration: 0.55, ease: "none",
          repeat: Math.ceil(D.dur / 0.55) }}, 0);
      }}
      window.__timelines["{cid}"] = tl;
    }})();
  </script>
</template>
"""
    return doc, dur


# --- captions, hook, end -------------------------------------------------------------------
def _grupos(palavras: list[dict]) -> list[list[dict]]:
    out, atual = [], []
    for w in palavras:
        atual.append(w)
        if len(atual) == 3 or re.search(r"[.,!?;:]$", w["texto"]):
            out.append(atual)
            atual = []
    if atual:
        out.append(atual)
    return out


def _legendas_html(tl: dict) -> str:
    blocos, tweens = [], []
    n = 0
    for f in tl["falas"]:
        grupos = _grupos(f["palavras"])
        for gi, g in enumerate(grupos):
            ini = g[0]["inicio"]
            prox = grupos[gi + 1][0]["inicio"] if gi + 1 < len(grupos) else f["fim"] + 0.15
            gid = f"leg{n}"
            spans = "".join(f'<span id="{gid}-w{wi}">{_esc(re.sub(r"[.,;:]$", "", w["texto"]).upper())}</span> '
                            for wi, w in enumerate(g))
            blocos.append(f'<div id="{gid}" class="clip leg" data-start="{ini:.3f}" '
                          f'data-duration="{max(0.2, prox - ini):.3f}" data-track-index="1">{spans.strip()}</div>')
            for wi, w in enumerate(g):
                tweens.append([f"#{gid}-w{wi}", round(w["inicio"], 3), round(w["fim"], 3)])
            n += 1
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; pointer-events: none; }}
    .leg {{ position: absolute; left: 120px; width: 660px; top: 1150px; text-align: center; z-index: 30; }}
    .leg span {{ display: inline-block; font-family: 'Archivo Black'; font-size: 64px; line-height: 1.05; color: #fff;
      -webkit-text-stroke: 13px #111; paint-order: stroke fill; margin: 0 6px; }}
  </style>
  <div id="root" data-composition-id="legendas" data-width="{L}" data-height="{A}">
    {''.join(blocos)}
  </div>
  <script>
    (function () {{
      const W = {json.dumps(tweens)};
      const tl = gsap.timeline({{ paused: true }});
      W.forEach(function (w) {{
        tl.set(w[0], {{ color: "{AMARELO}", scale: 1.12 }}, w[1]);
        tl.set(w[0], {{ color: "#ffffff", scale: 1 }}, Math.max(w[1] + 0.05, w[2]));
      }});
      window.__timelines["legendas"] = tl;
    }})();
  </script>
</template>
"""


def _gancho_html(rosto: str, titulo: str, dur: float) -> str:
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; background: #fafafa; overflow: hidden; }}
    #gancho-rosto {{ position: absolute; left: -35px; top: 640px; width: 1150px; height: 1150px; }}
    #gancho-titulo {{ position: absolute; left: 0; top: 230px; width: {L}px; }}
    #gancho-flash {{ position: absolute; inset: 0; background: #fff; opacity: 0; }}
  </style>
  <div id="root" data-composition-id="gancho" data-width="{L}" data-height="{A}">
    <img id="gancho-rosto" src="{rosto}" alt="">
    <img id="gancho-titulo" src="{titulo}" alt="">
    <div id="gancho-flash"></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#gancho-rosto", {{ scale: 1.0 }}, {{ scale: 1.12, duration: {dur}, ease: "none" }}, 0);
    tl.fromTo("#gancho-titulo", {{ scale: 1.06 }}, {{ scale: 1, duration: 0.15, ease: "power2.out" }}, 0);
    tl.fromTo("#gancho-flash", {{ opacity: 0 }}, {{ opacity: 0.9, duration: 0.1, ease: "none" }}, {dur - 0.1:.2f});
    window.__timelines["gancho"] = tl;
  </script>
</template>
"""


def _fim_html(ep: Episodio, dur: float) -> str:
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    #fim-veu {{ position: absolute; inset: 0; background: rgba(20, 20, 28, 0.82); }}
    .fim-t {{ position: absolute; left: 130px; width: 740px; text-align: center; font-family: 'Archivo Black'; }}
    #fim-continua {{ top: 420px; font-size: 100px; color: #fff; -webkit-text-stroke: 12px #111; paint-order: stroke fill; }}
    #fim-parte {{ top: 600px; font-size: 96px; color: {AMARELO}; -webkit-text-stroke: 12px #111; paint-order: stroke fill; }}
    #fim-pergunta {{ top: 790px; left: 120px; width: 660px; font-size: 46px; line-height: 1.15; color: #fff; }}
    #fim-segue {{ top: 1090px; left: 120px; width: 660px; font-size: 38px; color: #111; }}
    #fim-segue span {{ background: {AMARELO}; border: 6px solid #111; border-radius: 20px; padding: 10px 28px; }}
  </style>
  <div id="root" data-composition-id="fim" data-width="{L}" data-height="{A}">
    <div id="fim-veu"></div>
    <div id="fim-continua" class="fim-t">CONTINUA...</div>
    <div id="fim-parte" class="fim-t">{_esc(ep.proximo.upper())}</div>
    <div id="fim-pergunta" class="fim-t">{_esc(ep.pergunta)}</div>
    <div id="fim-segue" class="fim-t"><span>SEGUE PRA NÃO PERDER</span></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#fim-veu", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, 0);
    tl.fromTo("#fim-continua", {{ scale: 1.8, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.25, ease: "power3.out" }}, 0.1);
    tl.fromTo("#fim-parte", {{ scale: 0.4, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2)" }}, 0.45);
    tl.fromTo("#fim-pergunta", {{ y: 40, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.4 }}, 1.0);
    tl.fromTo("#fim-segue", {{ scale: 0.6, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2)" }}, 1.6);
    tl.to("#fim-segue", {{ scale: 1.06, duration: 0.4, yoyo: true, repeat: {max(1, int((dur - 2.0) / 0.4))},
      ease: "sine.inOut" }}, 2.0);
    window.__timelines["fim"] = tl;
  </script>
</template>
"""


def construir(ep: Episodio, timeline: Path, projeto: Path) -> Path:
    tl = json.loads(Path(timeline).read_text(encoding="utf-8"))
    comp = projeto / "compositions"
    assets = projeto / "assets"
    comp.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tl["audio"], assets / "audio.wav")
    dur = tl["duracao"]
    gancho_dur = 1.0
    hosts = []
    for ci in range(len(ep.cenas)):
        doc, d = _cena_html(ep, ci, tl, assets)
        (comp / f"cena{ci}.html").write_text(doc, encoding="utf-8")
        ini = tl["cenas"][ci]["inicio"]
        hosts.append(f'<div id="cena{ci}" data-composition-id="cena{ci}" data-composition-src="compositions/cena{ci}.html" '
                     f'data-start="{ini:.3f}" data-duration="{d:.3f}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{L}" data-height="{A}" style="z-index:1"></div>')
    (comp / "legendas.html").write_text(_legendas_html(tl), encoding="utf-8")
    rosto, titulo = _gancho_assets(ep, assets)
    (comp / "gancho.html").write_text(_gancho_html(rosto, titulo, gancho_dur), encoding="utf-8")
    fim_ini = tl["cartao"]
    (comp / "fim.html").write_text(_fim_html(ep, dur - fim_ini), encoding="utf-8")
    index = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8"><title>{_esc(ep.serie)} ep {ep.numero}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{L}" data-height="{A}">
      {''.join(hosts)}
      <div id="legendas" data-composition-id="legendas" data-composition-src="compositions/legendas.html" data-start="0"
        data-duration="{fim_ini:.3f}" data-track-index="2" data-track-kind="captions" data-width="{L}" data-height="{A}"
        style="z-index:5"></div>
      <div id="gancho" data-composition-id="gancho" data-composition-src="compositions/gancho.html" data-start="0"
        data-duration="{gancho_dur}" data-track-index="3" data-track-kind="graphics" data-width="{L}" data-height="{A}"
        style="z-index:8"></div>
      <div id="fim" data-composition-id="fim" data-composition-src="compositions/fim.html" data-start="{fim_ini:.3f}"
        data-duration="{dur - fim_ini:.3f}" data-track-index="3" data-track-kind="graphics" data-width="{L}"
        data-height="{A}" style="z-index:8"></div>
      <audio id="trilha" class="clip" src="assets/audio.wav" data-start="0" data-duration="{dur}" data-track-index="4"
        data-volume="1"></audio>
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
    (projeto / "index.html").write_text(index, encoding="utf-8")
    return projeto
