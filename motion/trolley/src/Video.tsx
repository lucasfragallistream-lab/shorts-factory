// "Você é o Maquinista" composition: 3D world + 2D characters (ThreeCanvas), camera, 2D layers, mixed audio.
// The world and the camera stop at CONGELA (freeze frame); the 2D layers and the audio keep the real time.
import React, {useMemo} from 'react';
import {AbsoluteFill, Audio, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig, delayRender, continueRender} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {camAt, kickAt, aplicar, type Cam} from './camera';
import {Mundo, HORIZONTE} from './mundo';
import {Elenco} from './ep3/elenco';
import {Legenda, Titulo, Contagem, Vinheta, Flash, Velocidade, Distancia, Congelamento} from './camadas';
import {pulso, smooth, chaveEm, EP, CONTAGEM, CONGELA} from './dados';

const fonte = new FontFace('Preta', `url(${staticFile('fonts/black.ttf')}) format('truetype')`);
const espera = delayRender('fonte das legendas');
fonte.load().then(() => { document.fonts.add(fonte); continueRender(espera); }).catch(() => continueRender(espera));

const Rig: React.FC<{c: Cam}> = ({c}) => { const {camera} = useThree(); aplicar(camera as THREE.PerspectiveCamera, c); return null; };

/** kit basic light: warm key sun with shadows around what the camera looks at, cool sky fill, a little ambient */
const Luzes: React.FC<{alvo: THREE.Vector3}> = ({alvo}) => {
  const target = useMemo(() => new THREE.Object3D(), []);
  target.position.set(alvo.x, 0, alvo.z); target.updateMatrixWorld();
  return (<>
    <primitive object={target} />
    <ambientLight intensity={0.3} color="#ffffff" />
    <hemisphereLight args={['#a9c4ee', '#c9a983', 0.95]} />
    <directionalLight position={[alvo.x + 8, 11, alvo.z + 7]} target={target} intensity={3.4} color="#fff3e0" castShadow
      shadow-mapSize={[2048, 2048]} shadow-camera-left={-22} shadow-camera-right={22} shadow-camera-top={22} shadow-camera-bottom={-22}
      shadow-camera-far={80} shadow-bias={-0.0004} />
  </>);
};

/** a clean take from an earlier episode (takes.mjs): the frame at that episode's time t - delta */
const Take: React.FC<{clip: string; f: number}> = ({clip, f}) => (
  <Sequence from={useCurrentFrame()} durationInFrames={1} layout="none">
    <OffthreadVideo src={staticFile(`takes/${clip}.mp4`)} startFrom={Math.max(0, f)} muted
      style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} />
  </Sequence>);

/** limpo: only the 3D world (no captions, HUD, overlays, camera kick or audio), to build the take bank */
export const Video: React.FC<{limpo?: boolean}> = ({limpo = false}) => {
  const f = useCurrentFrame(), {width, height} = useVideoConfig(), t = f / 30, k = width / 1080;
  const tc = Math.min(t, CONGELA);  // world time (frozen on the final card)
  const c = camAt(tc), [kx, ky] = limpo ? [0, 0] : kickAt(t);
  const ch = chaveEm(t);
  const take = !limpo && ch.clip && t < (ch.clip_ate ?? 99) ? {clip: ch.clip, f: Math.round((t - (ch.delta ?? 0)) * 30) - (ch.clip_f0 ?? 0)} : null;
  const cab = /^(cab_|lever|desvio|mao_|olho_)/.test(c.pose) || t >= CONTAGEM;
  const bate = cab && t < CONGELA && !limpo ? pulso(t) : 0;
  const gelo = t >= CONGELA && !limpo ? smooth((t - CONGELA) / 1.2) : 0;
  const filtros = limpo ? '' : [c.blur > 0.3 && t < CONGELA ? `blur(${c.blur * k}px)` : '',
    gelo ? `saturate(${1 - 0.45 * gelo}) contrast(${1 + 0.3 * gelo})` : ''].filter(Boolean).join(' ');
  return (
    <AbsoluteFill style={{backgroundColor: HORIZONTE}}>
      {!limpo && <Audio src={staticFile(`${EP}/audio.wav`)} />}
      <AbsoluteFill style={{transform: limpo ? undefined : `translate(${kx * k}px, ${ky * k}px) scale(${1.04 + 0.014 * bate + 0.06 * gelo})`,
        filter: filtros || undefined}}>
        {take ? <Take clip={take.clip} f={take.f} /> : (
          <ThreeCanvas width={width} height={height} shadows camera={{fov: 38, near: 0.03, far: 4000}} gl={{antialias: true}}>
            <color attach="background" args={[HORIZONTE]} />
            <fog attach="fog" args={[HORIZONTE, 80, 950]} />
            <Rig c={c} />
            <Luzes alvo={c.l} />
            <Mundo t={tc} />
            <Elenco t={tc} cam={c.p} />
          </ThreeCanvas>)}
      </AbsoluteFill>
      {!limpo && <Camadas t={t} k={k} linhas={t < CONGELA ? c.linhas : 0} />}
    </AbsoluteFill>
  );
};

const Camadas: React.FC<{t: number; k: number; linhas: number}> = ({t, k, linhas}) => (
  <>
      <Velocidade v={linhas} k={k} />
      <Vinheta t={t} />
      <Flash t={t} />
      <Congelamento t={t} />
      <Titulo t={t} k={k} />
      <Distancia t={t} k={k} />
      <Legenda t={t} k={k} />
      <Contagem t={t} k={k} />
  </>);
