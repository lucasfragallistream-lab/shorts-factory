// Flat 2D characters as camera-facing cards inside the 3D world (kit: 2D characters in a 3D toon world).
// Expressions/mouths follow the voice words and the event sheet (barks, lever pulls, the punchline).
import React from 'react';
import * as THREE from 'three';
import {useLoader} from '@react-three/fiber';
import {staticFile} from 'remotion';
import {ZF, CAB_Z, PISO, CAIXA, HELENA, CIDA, PANDA, FRASCO, PLACA_A, PLACA_B, TRILHO_Y, PUXADAS, SOLTA, LATIDOS,
  CONTAGEM, falando, palavra, cabeca} from './dados';

const NOMES = [
  ...['preocupado', 'chocado', 'raiva', 'triste'].flatMap((e) => ['fechada', 'aberta'].map((b) => `maquinista_${e}_${b}`)),
  ...['preocupado', 'feliz', 'chocado'].flatMap((e) => ['fechada', 'aberta'].map((b) => `helena_${e}_${b}`)),
  ...['triste', 'chocado'].flatMap((e) => ['fechada', 'aberta'].map((b) => `cida_${e}_${b}`)),
  ...[0, 1, 2].flatMap((i) => ['fechada', 'aberta'].map((b) => `filhote${i}_${b}`)),
  'panda', 'frasco', 'gota', 'placa_a', 'placa_b',
];
const URLS = NOMES.map((n) => staticFile(`ep1/sprites/${n}.png`));

const Card: React.FC<{tex: THREE.Texture; x: number; y: number; z: number; h: number; cam: THREE.Vector3; s?: number;
  centro?: boolean; luz?: boolean}> = ({tex, x, y, z, h, cam, s = 1, centro = false}) => {
  const img = tex.image as {width: number; height: number};
  const w = (h * img.width) / img.height, yaw = Math.atan2(cam.x - x, cam.z - z);
  return (<group position={[x, y, z]} rotation={[0, yaw, 0]} scale={[s, s, s]}>
    <mesh position={[0, centro ? 0 : h / 2, 0]}>
      <planeGeometry args={[w, h]} />
      <meshBasicMaterial map={tex} transparent alphaTest={0.02} toneMapped={false} side={THREE.DoubleSide} />
    </mesh>
  </group>);
};

const Sombra: React.FC<{x: number; y: number; z: number; r: number}> = ({x, y, z, r}) => (
  <mesh position={[x, y + 0.012, z]} rotation={[-Math.PI / 2, 0, 0]}>
    <circleGeometry args={[r, 20]} /><meshBasicMaterial color="#1b2a1b" transparent opacity={0.28} depthWrite={false} />
  </mesh>);

const em = (t: number, a: number, b: number) => t >= a && t < b;
const ALTURA_PESSOA = 1.95;  // figure canvas height in metres (feet at 596/600)

function maquinista(t: number): string {
  const ex = palavra('ex'), nadas = [palavra('Nada'), palavra('Nada', 2)];
  if (t >= CONTAGEM) {
    const s = Math.floor(t - CONTAGEM);
    if (t > 60.2) return 'chocado_aberta';
    return s % 2 ? 'chocado_fechada' : 'preocupado_fechada';
  }
  if (em(t, ex, ex + 2.3)) return 'chocado_aberta';
  if (em(t, ex + 2.3, ex + 3.6)) return 'triste_fechada';
  if (em(t, SOLTA, SOLTA + 1.4)) return 'chocado_aberta';
  for (const p of PUXADAS) if (em(t, p, p + 0.5)) return 'raiva_aberta';
  for (const n of nadas) if (em(t, n, n + 0.45)) return 'chocado_aberta';
  if (t < 3.4) return em(t, palavra('quebrar'), palavra('quebrar') + 0.5) ? 'chocado_aberta' : 'chocado_fechada';
  return 'preocupado_fechada';
}

function helena(t: number): string {
  const olha = palavra('olha');
  if (t >= CONTAGEM) return em(t, 55, 57) && (t * 3) % 1 < 0.45 ? 'preocupado_aberta' : 'preocupado_fechada';
  if (t >= olha) return falando('helena', t) ? 'feliz_aberta' : 'feliz_fechada';
  return 'preocupado_fechada';
}

function cida(t: number): string {
  if (falando('cida', t)) return 'triste_aberta';
  const soluco = (em(t, palavra('Cida'), 34.7) || em(t, 57, 59)) && (t * 2.6) % 1 < 0.3;
  return soluco ? 'triste_aberta' : 'triste_fechada';
}

const latindo = (i: number, t: number) => LATIDOS.some(([lt, c]) => c === i && t >= lt && t < lt + 0.22);

export const Personagens: React.FC<{t: number; cam: THREE.Vector3}> = ({t, cam}) => {
  const texs = useLoader(THREE.TextureLoader, URLS);
  const T: Record<string, THREE.Texture> = {};
  NOMES.forEach((n, i) => { const x = texs[i]; x.colorSpace = THREE.SRGBColorSpace; x.anisotropy = 8; T[n] = x; });
  const zf = ZF(t), h = cabeca(t);
  const filhotes = [[-4.62, -39.95, 0], [-4.25, -40.12, 1], [-3.9, -39.92, 2], [-3.55, -40.1, 0], [-4.1, -40.3, 2]];
  const pulsaA = em(t, palavra('trilho', 4), palavra('trilho', 4) + 1.2) || em(t, palavra('A', 4), palavra('A', 4) + 0.6);
  const pulsaB = em(t, palavra('B', 2), palavra('B', 2) + 0.6);
  const pz = (on: boolean, t0: number) => (on ? 1 + 0.18 * Math.abs(Math.sin((t - t0) * 9)) : 1);
  return (<>
    {/* the driver in the cab + sweat */}
    <Card tex={T[`maquinista_${maquinista(t)}`]} x={0.4} y={PISO} z={zf + CAB_Z} h={ALTURA_PESSOA} cam={cam} />
    {[0, 1].map((k) => { const fase = ((t + k * 0.45) % 0.9) / 0.9;
      return <Card key={k} tex={T.gota} x={h.x + 0.08} y={h.y + 0.12 - 0.4 * fase} z={h.z + (k ? 0.17 : -0.16)} h={0.09} cam={cam} centro />; })}
    {/* track A: five puppies in the box + Dr. Helena with the cure */}
    {filhotes.map(([x, z, tom], i) => (
      <Card key={i} tex={T[`filhote${tom}_${latindo(i, t) ? 'aberta' : 'fechada'}`]} x={x} y={CAIXA.y + 0.38 + 0.025 * Math.sin(t * 7 + i * 1.7) + (i === 4 ? 0.12 : 0)}
        z={z} h={0.62} cam={cam} />))}
    <Card tex={T[`helena_${helena(t)}`]} x={HELENA.x} y={HELENA.y} z={HELENA.z} h={ALTURA_PESSOA} cam={cam} />
    <Sombra x={HELENA.x} y={TRILHO_Y} z={HELENA.z} r={0.38} />
    <Card tex={T.frasco} x={FRASCO.x} y={FRASCO.y} z={FRASCO.z} h={0.42} cam={cam} centro s={1 + 0.06 * Math.sin(t * 6)} />
    {/* track B: grandma Cida hugging the last panda */}
    <Card tex={T[`cida_${cida(t)}`]} x={CIDA.x} y={CIDA.y} z={CIDA.z} h={ALTURA_PESSOA} cam={cam} />
    <Sombra x={CIDA.x} y={TRILHO_Y} z={CIDA.z} r={0.38} />
    <Card tex={T.panda} x={PANDA.x} y={PANDA.y} z={PANDA.z} h={0.62} cam={cam} s={1 + 0.02 * Math.sin(t * 2.2)} />
    {/* signs: text lives in the world */}
    <Card tex={T.placa_a} x={PLACA_A.x} y={6.6} z={PLACA_A.z} h={3.4} cam={cam} centro s={pz(pulsaA, 0)} />
    <Card tex={T.placa_b} x={PLACA_B.x} y={6.6} z={PLACA_B.z} h={3.4} cam={cam} centro s={pz(pulsaB, 0)} />
  </>);
};

