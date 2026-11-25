// Ep. 3 cast + props: the driver in the cab (and his bitten forearm), the vaccine case on track A, the scientist who
// made it on track B, crying, her lab coat caught under the rail. The brake/switch shots come from ep. 2 takes.
import React from 'react';
import * as THREE from 'three';
import {ZF, CAB_Z, PISO, TRILHO_Y, CONTAGEM, falando, palavra, cabeca, desvio, chaveEm} from '../dados';
import {Card, Sombra, Placas, useSprites, precarregar, em, ALTURA_PESSOA} from '../personagens';
import {MALETA, MALETA_H, DOUTORA, PANO, PANO_H, braco} from './lugares';

const NOMES = [
  ...['preocupado', 'chocado', 'raiva', 'triste'].flatMap((e) => ['fechada', 'aberta'].map((b) => `maquinista_${e}_${b}`)),
  'doutora_triste_fechada', 'doutora_triste_aberta', 'doutora_raiva_aberta', 'doutora_chocado_fechada',
  'maleta', 'braco_manga', 'braco_mordida', 'pano', 'mao', 'gota', 'placa_a', 'placa_b',
];
precarregar(NOMES);

function maquinista(t: number): string {
  const arde = palavra('arder'), uma = palavra('Uma', 2), dorm = palavra('dormindo');
  if (t >= CONTAGEM) return Math.floor((t - CONTAGEM) * 2) % 2 ? 'chocado_fechada' : 'preocupado_aberta';
  if (em(t, uma, dorm + 0.8)) return 'chocado_aberta';
  if (em(t, arde, uma)) return 'raiva_fechada';  // wincing
  if (t < palavra('Cem')) return 'chocado_fechada';
  return 'preocupado_fechada';
}

/** the scientist: crying, shouting "Socorro!", frozen when the train comes */
function doutora(t: number): string {
  if (falando('doutora', t)) return palavra('Socorro') <= t && t < palavra('Socorro') + 0.7 ? 'doutora_raiva_aberta' : 'doutora_triste_aberta';
  if (t >= CONTAGEM) return Math.floor(t * 3) % 2 ? 'doutora_triste_aberta' : 'doutora_triste_fechada';
  return Math.floor(t * 1.6) % 4 === 0 ? 'doutora_triste_aberta' : 'doutora_triste_fechada';  // sobbing
}

export const Elenco: React.FC<{t: number; cam: THREE.Vector3}> = ({t, cam}) => {
  const T = useSprites(NOMES);
  const zf = ZF(t), h = cabeca(t), dv = desvio(t), b = braco(t);
  const pose = chaveEm(t).pose;
  const mordido = t >= palavra('Uma', 2);
  const mao = t >= palavra('Só', 2) && t < palavra('Aí');
  const pulsaA = [palavra('A', 2), palavra('A', 7)].some((a) => em(t, a, a + 0.6));
  const pulsaB = [palavra('B'), palavra('B', 3)].some((x) => em(t, x, x + 0.6));
  const soluco = 0.012 * Math.max(0, Math.sin(t * 9));
  return (<>
    {/* the driver in the cab + sweat; his forearm only in its own close-ups */}
    <Card tex={T[`maquinista_${maquinista(t)}`]} x={0.4} y={PISO} z={zf + CAB_Z} h={ALTURA_PESSOA} cam={cam} />
    {[0, 1].map((k) => { const fase = ((t + k * 0.45) % 0.9) / 0.9;
      return <Card key={k} tex={T.gota} x={h.x + 0.08} y={h.y + 0.12 - 0.4 * fase} z={h.z + (k ? 0.17 : -0.16)} h={0.09} cam={cam} centro />; })}
    {pose.startsWith('braco') && <Card tex={T[mordido ? 'braco_mordida' : 'braco_manga']} x={b.x} y={b.y} z={b.z} h={0.19} cam={cam} centro
      rz={0.015 * Math.sin(t * 23)} />}
    {mao && <Card tex={T.mao} x={dv.x + 0.13} y={dv.y - 0.02} z={dv.z + 0.03} h={0.2} cam={cam} centro rz={t >= CONTAGEM ? 0.06 * Math.sin(t * 29) : 0} />}
    {/* track A: the vaccine case */}
    <Card tex={T.maleta} x={MALETA.x} y={MALETA.y} z={MALETA.z} h={MALETA_H} cam={cam} s={1 + 0.02 * Math.sin(t * 5)} />
    <Sombra x={MALETA.x} y={TRILHO_Y} z={MALETA.z} r={0.34} />
    {/* track B: the scientist, coat caught under the rail */}
    <Card tex={T[doutora(t)]} x={DOUTORA.x} y={DOUTORA.y + soluco} z={DOUTORA.z} h={ALTURA_PESSOA} cam={cam} />
    <Sombra x={DOUTORA.x} y={TRILHO_Y} z={DOUTORA.z} r={0.36} />
    <Card tex={T.pano} x={PANO.x} y={PANO.y} z={PANO.z} h={PANO_H} cam={cam} rz={0.05 * Math.sin(t * 13)} />
    <Placas a={T.placa_a} b={T.placa_b} cam={cam} t={t} pulsaA={pulsaA} pulsaB={pulsaB} />
  </>);
};
