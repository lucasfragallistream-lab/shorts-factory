// Flat 2D characters as camera-facing cards inside the 3D world (kit: 2D characters in a 3D toon world).
// Shared toolkit; each episode's cast and props live in src/epN/elenco.tsx.
import React from 'react';
import * as THREE from 'three';
import {staticFile, delayRender, continueRender, cancelRender} from 'remotion';
import {EP, PLACA_A, PLACA_B} from './dados';

export const ALTURA_PESSOA = 1.95;  // figure canvas height in metres (feet at 596/600)
export const em = (t: number, a: number, b: number) => t >= a && t < b;

// Sprites are loaded BEFORE any frame is captured (delayRender at module load). Loading them inside the canvas with a
// suspending loader blanked the whole 3D scene on the first frame a tab renders (the Suspense hides every child).
const TEXTURAS = new Map<string, THREE.Texture>();
export function precarregar(nomes: string[]) {
  const h = delayRender(`sprites ${EP}`);
  const loader = new THREE.TextureLoader();
  Promise.all(nomes.map((n) => loader.loadAsync(staticFile(`${EP}/sprites/${n}.png`)).then((x) => {
    x.colorSpace = THREE.SRGBColorSpace; x.anisotropy = 8; TEXTURAS.set(n, x);
  }))).then(() => continueRender(h)).catch((e) => cancelRender(e));
}
/** all sprites of the episode as textures, by name (preloaded) */
export function useSprites(nomes: string[]): Record<string, THREE.Texture> {
  const T: Record<string, THREE.Texture> = {};
  for (const n of nomes) { const x = TEXTURAS.get(n); if (!x) throw new Error(`sprite não carregado: ${n}`); T[n] = x; }
  return T;
}

export const Card: React.FC<{tex: THREE.Texture; x: number; y: number; z: number; h: number; cam: THREE.Vector3; s?: number;
  centro?: boolean; rz?: number}> = ({tex, x, y, z, h, cam, s = 1, centro = false, rz = 0}) => {
  const img = tex.image as {width: number; height: number};
  const w = (h * img.width) / img.height, yaw = Math.atan2(cam.x - x, cam.z - z);
  return (<group position={[x, y, z]} rotation={[0, yaw, 0]} scale={[s, s, s]}>
    <mesh position={[0, centro ? 0 : h / 2, 0]} rotation={[0, 0, rz]}>
      <planeGeometry args={[w, h]} />
      <meshBasicMaterial map={tex} transparent alphaTest={0.02} toneMapped={false} side={THREE.DoubleSide} />
    </mesh>
  </group>);
};

export const Sombra: React.FC<{x: number; y: number; z: number; r: number}> = ({x, y, z, r}) => (
  <mesh position={[x, y + 0.012, z]} rotation={[-Math.PI / 2, 0, 0]}>
    <circleGeometry args={[r, 20]} /><meshBasicMaterial color="#1b2a1b" transparent opacity={0.28} depthWrite={false} />
  </mesh>);

/** the A/B signs at the fork (text lives in the world); pulse while their letter is spoken */
export const Placas: React.FC<{a: THREE.Texture; b: THREE.Texture; cam: THREE.Vector3; t: number; pulsaA: boolean; pulsaB: boolean}> =
  ({a, b, cam, t, pulsaA, pulsaB}) => {
    const pz = (on: boolean) => (on ? 1 + 0.18 * Math.abs(Math.sin(t * 9)) : 1);
    return (<>
      <Card tex={a} x={PLACA_A.x} y={6.6} z={PLACA_A.z} h={3.4} cam={cam} centro s={pz(pulsaA)} />
      <Card tex={b} x={PLACA_B.x} y={6.6} z={PLACA_B.z} h={3.4} cam={cam} centro s={pz(pulsaB)} />
    </>);
  };
