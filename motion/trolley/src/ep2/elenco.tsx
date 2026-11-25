// Ep. 2 cast + props: the driver in the cab, Paçoca with the winning ticket on track A, five grandpas playing
// dominoes on track B (the fifth, holding a bread bag, is the father). Expressions and gestures follow the voice.
import React from 'react';
import * as THREE from 'three';
import {ZF, CAB_Z, PISO, TRILHO_Y, PUXADAS, SOLTA, LATIDOS, CONTAGEM, falando, palavra, cabeca, desvio} from '../dados';
import {Card, Sombra, Placas, useSprites, precarregar, em, ALTURA_PESSOA} from '../personagens';
import {toon} from '../mundo';
import {PACOCA, PACOCA_H, BILHETE, BILHETE_H, MESA, MESA_TOPO, VOVOS, PAI} from './lugares';

const NOMES = [
  ...['preocupado', 'chocado', 'raiva', 'triste'].flatMap((e) => ['fechada', 'aberta'].map((b) => `maquinista_${e}_${b}`)),
  ...[1, 2, 3, 4].flatMap((i) => ['fechada', 'aberta'].map((b) => `vovo${i}_feliz_${b}`)), 'vovo1_bati',
  ...['feliz', 'pao'].flatMap((e) => ['fechada', 'aberta'].map((b) => `pai_${e}_${b}`)),
  ...['fechada', 'aberta'].flatMap((b) => [0, 1].map((r) => `pacoca_${b}_${r}`)),
  'bilhete', 'mao', 'gota', 'placa_a', 'placa_b',
];
precarregar(NOMES);

function maquinista(t: number): string {
  const pai = palavra('pai'), nada = palavra('Nada'), oi = palavra('Oi');
  if (t >= CONTAGEM) {
    if (t > 58.9) return 'chocado_aberta';
    return Math.floor((t - CONTAGEM) * 2) % 2 ? 'chocado_fechada' : 'preocupado_aberta';
  }
  if (em(t, pai, pai + 2.3)) return 'chocado_aberta';
  if (em(t, pai + 2.3, oi + 1.2)) return 'chocado_fechada';
  if (em(t, oi + 1.2, oi + 3.2)) return 'raiva_fechada';
  if (em(t, SOLTA, SOLTA + 1.4)) return 'chocado_aberta';
  for (const p of PUXADAS) if (em(t, p, p + 0.5)) return 'raiva_aberta';
  if (em(t, nada, nada + 0.45)) return 'chocado_aberta';
  if (t < 3.6) return 'chocado_fechada';
  return 'preocupado_fechada';
}

const latindo = (t: number) => LATIDOS.some(([lt]) => t >= lt && t < lt + 0.22);

/** laughing windows of the grandpas (match the laughter cues in plano.json) */
const rindo = (t: number) => em(t, palavra('pilha') + 0.3, palavra('pilha') + 2.3) || em(t, palavra('Bati', 2) + 0.35, palavra('Bati', 2) + 1.95);

const Mesa: React.FC<{t: number}> = ({t}) => {
  const b1 = palavra('Bati'), b2 = palavra('Bati', 2);
  const salto = [b1, b2].reduce((m, b) => (t >= b && t < b + 0.3 ? Math.max(m, Math.sin(Math.PI * (t - b) / 0.3)) : m), 0) * 0.05;
  const y = MESA.y + MESA_TOPO;
  return (<group position={[MESA.x, 0, MESA.z]}>
    <mesh position={[0, y, 0]} castShadow receiveShadow><boxGeometry args={[1.3, 0.06, 0.78]} /><primitive object={toon('#7a4b2c')} attach="material" /></mesh>
    {[[-0.58, -0.32], [0.58, -0.32], [-0.58, 0.32], [0.58, 0.32]].map(([x, z], i) => (
      <mesh key={i} position={[x, MESA.y + MESA_TOPO / 2, z]} castShadow><boxGeometry args={[0.06, MESA_TOPO, 0.06]} />
        <primitive object={toon('#5e3820')} attach="material" /></mesh>))}
    {Array.from({length: 9}, (_, i) => (
      <mesh key={`d${i}`} position={[-0.42 + i * 0.105, y + 0.04 + salto * (i % 2 ? 1 : 0.6), 0.02 + (i % 3) * 0.015]}
        rotation={[0, i % 3 === 1 ? Math.PI / 2 : 0, 0]} castShadow>
        <boxGeometry args={[0.05, 0.015, 0.1]} /><primitive object={toon('#f4f1e8')} attach="material" /></mesh>))}
    {[[-0.45, 0.3], [-0.15, -0.3], [0.2, -0.3], [0.5, 0.25]].map(([x, z], i) => (
      <mesh key={`m${i}`} position={[x, y + 0.08 + salto, z]} castShadow>
        <boxGeometry args={[0.16, 0.1, 0.02]} /><primitive object={toon('#f4f1e8')} attach="material" /></mesh>))}
  </group>);
};

export const Elenco: React.FC<{t: number; cam: THREE.Vector3}> = ({t, cam}) => {
  const T = useSprites(NOMES);
  const zf = ZF(t), h = cabeca(t), dv = desvio(t);
  const ele = palavra('Ele'), trouxe = palavra('Trouxe');
  const feliz = t >= ele;  // he sees you coming: tail wags
  const rabo = Math.floor(t * (feliz ? 7 : 2.5)) % 2;
  const boca = latindo(t) || (feliz && em(t, ele, ele + 2.2) && Math.floor(t * 4) % 2 === 0) ? 'aberta' : 'fechada';
  const bati = falando('vovo', t) || em(t, palavra('Bati'), palavra('Bati') + 0.9) || em(t, palavra('Bati', 2), palavra('Bati', 2) + 0.9);
  const ri = rindo(t);
  const vovoBoca = (i: number) => (ri && Math.floor(t * 6 + i) % 2 === 0) || (!ri && Math.floor(t * 1.3 + i * 0.7) % 5 === 0) ? 'aberta' : 'fechada';
  const paiSprite = `pai_${t >= trouxe ? 'pao' : 'feliz'}_${falando('pai', t) ? 'aberta' : 'fechada'}`;
  const mao = t >= palavra('Só');
  const pulsaA = [palavra('A'), palavra('A', 2), palavra('A', 3)].some((a) => em(t, a, a + 0.6));
  const pulsaB = [palavra('B'), palavra('B', 2)].some((b) => em(t, b, b + 0.6));
  return (<>
    {/* the driver in the cab + sweat */}
    <Card tex={T[`maquinista_${maquinista(t)}`]} x={0.4} y={PISO} z={zf + CAB_Z} h={ALTURA_PESSOA} cam={cam} />
    {[0, 1].map((k) => { const fase = ((t + k * 0.45) % 0.9) / 0.9;
      return <Card key={k} tex={T.gota} x={h.x + 0.08} y={h.y + 0.12 - 0.4 * fase} z={h.z + (k ? 0.17 : -0.16)} h={0.09} cam={cam} centro />; })}
    {mao && <Card tex={T.mao} x={dv.x + 0.13} y={dv.y - 0.02} z={dv.z + 0.03} h={0.2} cam={cam} centro rz={t >= CONTAGEM ? 0.06 * Math.sin(t * 29) : 0} />}
    {/* track A: Paçoca + the winning ticket on his collar */}
    <Card tex={T[`pacoca_${boca}_${rabo}`]} x={PACOCA.x} y={PACOCA.y + 0.015 * Math.abs(Math.sin(t * 7))} z={PACOCA.z} h={PACOCA_H} cam={cam} />
    <Sombra x={PACOCA.x} y={TRILHO_Y} z={PACOCA.z} r={0.36} />
    <Card tex={T.bilhete} x={BILHETE.x} y={BILHETE.y} z={BILHETE.z} h={BILHETE_H} cam={cam} centro
      s={1 + 0.05 * Math.sin(t * 6)} rz={0.08 * Math.sin(t * 3.1)} />
    {/* track B: the domino table, four grandpas + the father */}
    <Mesa t={t} />
    {VOVOS.map((p, i) => (
      <Card key={i} tex={T[i === 0 && bati ? 'vovo1_bati' : `vovo${i + 1}_feliz_${vovoBoca(i)}`]} x={p.x} y={p.y} z={p.z} h={ALTURA_PESSOA} cam={cam} />))}
    {VOVOS.map((p, i) => <Sombra key={`s${i}`} x={p.x} y={TRILHO_Y} z={p.z} r={0.34} />)}
    <Card tex={T[paiSprite]} x={PAI.x} y={PAI.y} z={PAI.z} h={ALTURA_PESSOA} cam={cam} />
    <Sombra x={PAI.x} y={TRILHO_Y} z={PAI.z} r={0.36} />
    <Placas a={T.placa_a} b={T.placa_b} cam={cam} t={t} pulsaA={pulsaA} pulsaB={pulsaB} />
  </>);
};
