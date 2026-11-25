// Ep. 3 world spots: the last zombie vaccine in a case on track A, the scientist who made it on track B (her lab coat
// caught under the right rail), the driver's forearm in the cab (the bite).
import {V, add, TRILHO_Y, cabeca} from '../dados';

export const MALETA = V(-4, TRILHO_Y, -40);
export const MALETA_H = 0.42;
export const DOUTORA = V(4.42, TRILHO_Y, -40);
export const PANO = V(4.66, TRILHO_Y + 0.02, -39.82);  // coat corner under the rail
export const PANO_H = 0.16;
/** the driver's forearm, in front of his lap (beige trousers behind the blue sleeve; the cab cameras look from +x) */
export const braco = (t: number) => add(cabeca(t), 0.34, -0.92, -0.04);
