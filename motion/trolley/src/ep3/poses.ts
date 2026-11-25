// Ep. 3 camera poses (the generic train/cab/fork poses live in ../camera.ts).
import {P, V, add, type Pose} from '../dados';
import {MALETA, DOUTORA, PANO, braco} from './lugares';

export const POSES_EP: Record<string, (t: number) => Pose> = {
  vacina_ms: () => P(V(-3.35, 1.05, -37.3), add(MALETA, 0, 0.24, 0), 38),
  vacina_cu: () => P(V(-3.72, 0.78, -38.8), add(MALETA, 0, 0.22, 0), 36),
  vacina_ecu: () => P(V(-3.9, 0.66, -39.32), add(MALETA, 0, 0.27, 0), 32),
  // hook: the case sits low in the frame, under the giant title
  vacina_gancho: () => P(V(-3.9, 0.9, -38.45), add(MALETA, 0, 0.587, 0), 34),  // 1.6 m back: label + vial fit below the caption
  doutora_ms: () => P(add(DOUTORA, -0.3, 1.4, 3.7), add(DOUTORA, 0, 1.0, 0), 38),
  doutora_cu: () => P(add(DOUTORA, -0.12, 1.5, 2.15), add(DOUTORA, 0, 1.36, 0), 36),
  // the whole crying face (bun to collar), sitting low enough to clear the title
  doutora_rosto: () => P(add(DOUTORA, -0.06, 1.56, 1.25), add(DOUTORA, 0, 1.56, 0), 34),
  doutora_ecu: () => P(add(DOUTORA, -0.04, 1.5, 0.8), add(DOUTORA, 0, 1.47, 0), 30),
  jaleco_cu: () => P(add(DOUTORA, -0.55, 0.6, 1.75), add(DOUTORA, 0.12, 0.42, 0), 38),
  braco_cu: (t) => P(add(braco(t), 0.92, 0.2, -0.2), add(braco(t), 0, 0, 0), 36),
  braco_ecu: (t) => P(add(braco(t), 0.52, 0.08, -0.08), add(braco(t), 0.02, 0, 0), 30),
};
