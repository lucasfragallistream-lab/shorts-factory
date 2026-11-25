// Continuous-take camera (kit references/03_CAMERA_GRAMMAR.md): every key LANDS on its word, moves are eased with the
// velocity peak at ~40 %, the camera creeps in during holds (never still), push-in is the default, pull-backs reveal,
// whips hide staging changes, one hard cut. Poses may follow the moving train.
import * as THREE from 'three';
import {CHAVES, KICKS, V, ZF, cabeca, freio, desvio, CAIXA, HELENA, CIDA, PANDA, FRASCO, ease40, cl, type Chave} from './dados';

export type Pose = {p: THREE.Vector3; l: THREE.Vector3; fov: number};
const P = (p: THREE.Vector3, l: THREE.Vector3, fov: number): Pose => ({p, l, fov});
const add = (a: THREE.Vector3, x: number, y: number, z: number) => a.clone().add(V(x, y, z));

export const POSES: Record<string, (t: number) => Pose> = {
  cab_ecu: (t) => P(add(cabeca(t), 0.95, 0.05, -0.3), add(cabeca(t), 0, -0.03, 0), 34),
  cab_mcu: (t) => P(add(cabeca(t), 2.0, 0.1, -0.9), add(cabeca(t), 0, -0.4, 0), 40),
  cab_shock: (t) => P(add(cabeca(t), 0.72, 0.0, -0.12), add(cabeca(t), 0, 0, 0), 30),
  cab_extreme: (t) => P(add(cabeca(t), 0.62, 0.02, -0.08), add(cabeca(t), 0, 0, 0), 27),
  lever_cu: (t) => P(add(freio(t), 0.95, 0.2, 0.12), add(freio(t), 0, -0.12, 0.05), 40),
  desvio_cu: (t) => P(add(desvio(t), 1.05, 0.22, 0.15), add(desvio(t), 0, -0.15, 0), 40),
  train_side: (t) => P(V(15, 3, ZF(t) + 4), V(0, 2.2, ZF(t) + 12), 40),
  wheels_low: (t) => P(V(3.4, 0.75, ZF(t) - 4), V(1.0, 1.15, ZF(t) + 4), 46),
  fork_aerial: () => P(V(0, 24, 28), V(0, 0, -22), 42),
  fork_a: () => P(V(-1.2, 8, 9), V(-6.6, 3.2, -14), 42),
  box_ms: () => P(V(-3.3, 1.9, -36.6), add(CAIXA, 0, 0.7, 0), 38),
  puppies_ecu: () => P(V(-3.95, 1.55, -38.35), add(CAIXA, -0.05, 0.85, 0), 40),
  helena_ms: () => P(V(-1.5, 1.75, -36.2), add(HELENA, 0, 1.05, 0), 38),
  vial_cu: () => P(add(FRASCO, 0.12, 0.1, 0.95), FRASCO.clone(), 34),
  cida_ms: () => P(V(3.3, 1.75, -36.4), add(CIDA, 0, 1.05, 0), 38),
  cida_cu: () => P(V(3.9, 2.0, -38.75), add(CIDA, 0, 1.55, 0), 34),
  panda_cu: () => P(add(PANDA, -0.08, 0.42, 1.0), add(PANDA, 0, 0.28, 0), 34),
  helena_face: () => P(V(-2.0, 1.9, -37.9), add(HELENA, 0, 1.5, 0), 36),
  helena_ecu: () => P(V(-2.2, 1.86, -38.85), add(HELENA, 0, 1.52, 0), 32),
  helena_smug: () => P(V(-2.1, 1.84, -38.7), add(HELENA, 0, 1.52, 0), 34),
  group_a: () => P(V(-2.6, 2.3, -33.6), V(-3.2, 2.7, -40), 46),   // subjects in the lower third (countdown cards in the middle)
  group_b: () => P(V(4.4, 2.4, -34.8), add(CIDA, 0, 2.35, 0), 42),
  approach: (t) => P(V(7, 13, ZF(t) + 26), V(0, 1.5, ZF(t) - 60), 50),
  approach_a: (t) => P(V(5.5, 13, ZF(t) + 26), V(-10, 1.5, ZF(t) - 60), 50),
  approach_b: (t) => P(V(8.5, 13, ZF(t) + 26), V(10, 1.5, ZF(t) - 60), 50),
};

const DEF_CREEP = 0.03;  // fraction of the subject distance per second (kit: never hold still)
function poseDe(k: Chave, t: number): Pose {
  const base = POSES[k.pose](t);
  const dt = Math.max(0, t - k.t), c = cl(1 - (k.creep ?? DEF_CREEP) * dt, 0.55, 1);
  return {p: base.l.clone().add(base.p.clone().sub(base.l).multiplyScalar(c)), l: base.l, fov: base.fov};
}

export type Cam = Pose & {roll: number; blur: number; linhas: number};
/** camera at real time t (seconds) */
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
  return {...pose, roll, blur, linhas};
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
  cam.rotateZ((c.roll * Math.PI) / 180);
  if (cam.fov !== c.fov) { cam.fov = c.fov; cam.updateProjectionMatrix(); }
}
