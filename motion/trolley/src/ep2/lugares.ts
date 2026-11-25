// Ep. 2 world spots: Paçoca + the ticket on track A, five grandpas around a domino table on track B (one is the father).
import {V, add, TRILHO_Y} from '../dados';

export const PACOCA = V(-4, TRILHO_Y, -40);
export const PACOCA_H = 0.85;                      // card height (sitting dog)
export const BILHETE = V(-4, TRILHO_Y + 0.24, -39.86);
export const BILHETE_H = 0.17;
export const MESA = V(4, TRILHO_Y, -40.3);          // domino table, top at +0.92
export const MESA_TOPO = 0.92;
export const VOVOS = [V(3.05, TRILHO_Y, -40.15), V(3.7, TRILHO_Y, -40.95), V(4.35, TRILHO_Y, -40.95), V(4.98, TRILHO_Y, -40.35)];
export const V1 = VOVOS[0];                          // the one who slams "Bati!"
export const PAI = V(5.35, TRILHO_Y, -39.6);
export const SACO = add(PAI, 0.25, 0.35, 0);         // bread bag hanging from his hand (drawn in his sprite)
export const SACO_ALTO = add(PAI, 0.84, 0.85, 0);    // bag held out on "Trouxe o pão"
