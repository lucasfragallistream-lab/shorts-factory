// Ep. 2 camera poses (the generic train/cab/fork poses live in ../camera.ts).
import {P, V, add, type Pose} from '../dados';
import {PACOCA, BILHETE, MESA, V1, PAI, SACO, SACO_ALTO} from './lugares';

export const POSES_EP: Record<string, (t: number) => Pose> = {
  pacoca_ms: () => P(V(-3.3, 1.25, -37.0), add(PACOCA, 0, 0.42, 0), 38),
  pacoca_cu: () => P(V(-3.7, 0.9, -38.55), add(PACOCA, 0, 0.48, 0), 36),
  pacoca_ecu: () => P(V(-3.88, 0.8, -39.15), add(PACOCA, 0, 0.6, 0), 34),
  bilhete_cu: () => P(add(BILHETE, 0.25, 0.18, 1.5), add(BILHETE, 0, 0.05, 0), 36),
  bilhete_ecu: () => P(add(BILHETE, 0.06, 0.04, 1.05), BILHETE.clone(), 32),
  vovos_ms: () => P(V(4.2, 2.0, -33.3), add(MESA, 0, 1.1, -0.2), 42),
  domino_cu: () => P(add(MESA, -0.35, 1.7, 1.1), add(MESA, 0.05, 0.95, 0), 38),
  vovos_low: () => P(V(3.3, 0.55, -36.8), add(MESA, 0.3, 1.45, -0.3), 46),
  vovo_bati: () => P(add(V1, 0.45, 1.45, 1.9), add(V1, 0, 1.35, 0), 40),
  pai_ms: () => P(add(PAI, 0.25, 1.45, 3.4), add(PAI, 0, 1.05, 0), 38),
  saco_cu: () => P(add(SACO, 0.15, 0.12, 1.0), SACO.clone(), 36),
  pai_face: () => P(add(PAI, 0.1, 1.55, 1.55), add(PAI, 0, 1.5, 0), 36),
  pai_ecu: () => P(add(PAI, 0.04, 1.43, 0.72), add(PAI, 0, 1.42, 0), 30),
  pai_smug: () => P(add(PAI, -0.12, 1.5, 1.05), add(PAI, 0, 1.47, 0), 34),
  pai_pao: () => P(add(SACO_ALTO, -0.3, 0.3, 3.2), add(SACO_ALTO, -0.42, 0.25, 0), 40),
};
