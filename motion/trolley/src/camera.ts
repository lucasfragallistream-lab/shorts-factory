// Camera (kit references/03_CAMERA_GRAMMAR.md): every key LANDS on its word, moves are eased with the velocity peak at
// ~40 %, the camera creeps in during holds (never still), push-in is the default, pull-backs reveal, whips hide staging
// changes. Thriller layer (ep. 2 notes): constant vibration in and around the train (100 t shaking the cab), a subtle
// handheld drift elsewhere, dutch angles on panic keys (roll), 0.8 s train inserts and the accelerating countdown montage
// are hard cuts tagged in the plan.
import * as THREE from 'three';
import {CHAVES, KICKS, CONTAGEM, V, P, add, ZF, cabeca, freio, desvio, ease40, cl, type Chave, type Pose} from './dados';
import {POSES_EP} from './ep3/poses';

export type {Pose};

export const POSES: Record<string, (t: number) => Pose> = {
  cab_ecu: (t) => P(add(cabeca(t), 0.95, 0.05, -0.3), add(cabeca(t), 0, -0.03, 0), 34),
  cab_mcu: (t) => P(add(cabeca(t), 2.0, 0.1, -0.9), add(cabeca(t), 0, -0.4, 0), 40),
  cab_shock: (t) => P(add(cabeca(t), 0.72, 0.0, -0.12), add(cabeca(t), 0, 0, 0), 30),
  cab_extreme: (t) => P(add(cabeca(t), 0.62, 0.02, -0.08), add(cabeca(t), 0, 0, 0), 27),
  olho_ecu: (t) => P(add(cabeca(t), 0.55, 0.07, -0.06), add(cabeca(t), 0, 0.06, 0), 34),
  // over the driver's shoulder: the brake lever swings toward the lens on every pull, the track ahead in the windows
  lever_cu: (t) => P(V(-0.65, 3.05, ZF(t) + 7.75), V(-0.3, 2.5, ZF(t) + 6.25), 46),
  lever_ecu: (t) => P(V(-0.6, 3.0, ZF(t) + 7.75), V(-0.3, 2.38, ZF(t) + 6.45), 44),
  desvio_cu: (t) => P(add(desvio(t), 1.05, 0.22, 0.15), add(desvio(t), 0, -0.15, 0), 40),
  mao_alavanca: (t) => P(add(desvio(t), 0.62, 0.12, 0.14), add(desvio(t), 0, -0.04, 0), 36),
  train_side: (t) => P(V(15, 3, ZF(t) + 4), V(0, 2.2, ZF(t) + 12), 40),
  wheels_low: (t) => P(V(3.4, 0.75, ZF(t) - 4), V(1.0, 1.15, ZF(t) + 4), 46),
  rails_skim: (t) => P(V(1.5, 0.5, ZF(t) - 2.8), V(0.75, 0.8, ZF(t) + 2.4), 44),
  roda_ecu: (t) => P(V(2.15, 0.62, ZF(t) + 0.9), V(1.05, 0.72, ZF(t) + 2.6), 40),
  trilho_frente: (t) => P(V(0, 2.55, ZF(t) - 1.1), V(0, 0.4, ZF(t) - 70), 48),
  final_switch: (t) => P(V(1.9, 0.62, -7.2), V(0.25, 1.9, Math.max(3.5, ZF(t) + 1.5)), 50),
  fork_aerial: () => P(V(0, 24, 28), V(0, 0, -22), 42),
  fork_a: () => P(V(-1.2, 8, 9), V(-6.6, 3.2, -14), 42),
  approach: (t) => P(V(6, 9, ZF(t) + 22), V(0, 0.5, ZF(t) - 30), 50),
  approach_a: (t) => P(V(4.5, 9, ZF(t) + 22), V(-6, 0.5, ZF(t) - 30), 50),
  approach_b: (t) => P(V(7.5, 9, ZF(t) + 22), V(6, 0.5, ZF(t) - 30), 50),
  ...POSES_EP,
};

const DEF_CREEP = 0.03;  // fraction of the subject distance per second (kit: never hold still)
function poseDe(k: Chave, t: number): Pose {
  const f = POSES[k.pose];
  if (!f) throw new Error(`pose desconhecida: ${k.pose}`);
  const base = f(t);
  const dt = Math.max(0, t - k.t), c = cl(1 - (k.creep ?? (k.tag === 'montagem' ? 0.09 : DEF_CREEP)) * dt, 0.55, 1);
  const p = base.l.clone().add(base.p.clone().sub(base.l).multiplyScalar(c)), l = base.l.clone();
  if (k.tag === 'montagem') {  // pedestal down: the subject rises above the countdown ring (cards on top, ring low)
    const dy = 0.12 * 2 * p.distanceTo(l) * Math.tan((base.fov * Math.PI) / 360);
    p.y -= dy; l.y -= dy;
  }
  return {p, l, fov: base.fov};
}

// vibration classes: inside the cab (strong rattle), on/near the train (medium), anywhere else (handheld drift)
const CABINE = /^(cab_|lever|desvio|mao_|olho_)/;
const NO_TREM = /^(train_side|wheels_low|rails_skim|roda_ecu|trilho_frente|approach|final_switch)/;
const ondas = (t: number, fs: number[], fase: number) => fs.reduce((s, f, i) => s + Math.sin(2 * Math.PI * f * t + fase + i * 1.7), 0) / fs.length;
/** shake in screen px (1080x1920 units) + roll degrees for the pose active at t */
export function tremor(pose: string, t: number): {x: number; y: number; r: number} {
  const forte = CABINE.test(pose) ? 1 : NO_TREM.test(pose) ? 0.75 : 0;
  const conta = t >= CONTAGEM ? 1.45 : 1;
  const hf = (9 * forte) * conta, lf = (forte ? 9 : 5) * conta, deriva = forte ? 4 : 9;
  const x = hf * ondas(t, [13.1, 17.3, 23.7], 0.3) + lf * ondas(t, [1.7, 2.9], 1.1) + deriva * ondas(t, [0.31, 0.47], 2.2);
  const y = hf * ondas(t, [11.3, 19.1, 26.9], 2.9) + lf * ondas(t, [2.3, 3.7], 0.4) + deriva * ondas(t, [0.27, 0.53], 0.9);
  const r = (0.5 * forte * conta) * ondas(t, [7.1, 12.7], 0.6) + 0.25 * ondas(t, [0.4], 1.3);
  return {x, y, r};
}

export type Cam = Pose & {roll: number; blur: number; linhas: number; sx: number; sy: number; pose: string; tag?: string};
/** camera at time t (seconds; pass the frozen time on the final freeze) */
export function camAt(t: number): Cam {
  // a move starts `dur` before its word, but never before the previous key has landed (no overlapping moves)
  const inicio = (j: number) => { const c = CHAVES[j]; const d = c.move === 'cut' ? 0 : c.dur ?? 0.6;
    return j > 0 ? Math.max(c.t - d, CHAVES[j - 1].t) : 0; };
  let i = 0;
  while (i + 1 < CHAVES.length && inicio(i + 1) <= t) i++;
  const k = CHAVES[i];
  const atual = poseDe(k, t);
  const ant = i > 0 ? CHAVES[i - 1] : null;
  const d = k.t - inicio(i);
  let pose = atual, roll = k.roll ?? 0, blur = 0, linhas = 0;
  if (ant && d > 0 && t < k.t) {
    const u = cl((t - (k.t - d)) / d), e = ease40(u), de = poseDe(ant, t);
    const p = de.p.clone().lerp(atual.p, e), l = de.l.clone().lerp(atual.l, e);
    if (k.move === 'fly') p.y += Math.min(30, Math.max(4.5, de.p.distanceTo(atual.p) * 0.18)) * Math.sin(Math.PI * e);
    pose = {p, l, fov: de.fov + (atual.fov - de.fov) * e};
    roll = (ant.roll ?? 0) + ((k.roll ?? 0) - (ant.roll ?? 0)) * e;
    const s = Math.sin(Math.PI * u);
    blur = k.move === 'whip' ? 16 * s : k.move === 'fly' ? 9 * s : 2.5 * s * Math.min(1, de.p.distanceTo(atual.p) / 3);
    linhas = k.move === 'fly' ? s : 0;
  }
  const sh = tremor(k.pose, t);
  // inserts and the first frames of the hook rush past: speed lines + a touch of blur
  if (k.tag === 'insert' || k.pose === 'rails_skim') { linhas = Math.max(linhas, 0.8); blur = Math.max(blur, 1.2); }
  return {...pose, roll: roll + sh.r, blur, linhas, sx: sh.x, sy: sh.y, pose: k.pose, tag: k.tag};
}

/** screen shake in px (flip sign every frame, dies in 7 frames: kit impact kick) */
export function kickAt(t: number): [number, number] {
  let x = 0, y = 0;
  for (const [tk, a] of KICKS) {
    const f = Math.floor((t - tk) * 30);
    if (f < 0 || f > 7) continue;
    const s = a * (1 - f / 7) * (f % 2 ? 1 : -1);
    x += s; y -= s * 0.5;
  }
  return [x, y];
}

export function aplicar(cam: THREE.PerspectiveCamera, c: Cam) {
  cam.position.copy(c.p);
  cam.up.set(0, 1, 0);
  cam.lookAt(c.l);
  // vibration as a tiny camera rotation: px on screen -> degrees through the vertical fov
  cam.rotateY((-c.sx / 1920) * c.fov * (Math.PI / 180));
  cam.rotateX((c.sy / 1920) * c.fov * (Math.PI / 180));
  cam.rotateZ((c.roll * Math.PI) / 180);
  if (cam.fov !== c.fov) { cam.fov = c.fov; cam.updateProjectionMatrix(); }
}
