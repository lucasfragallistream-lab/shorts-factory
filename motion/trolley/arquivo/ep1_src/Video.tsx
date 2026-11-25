// "Você é o Maquinista" composition: 3D world + 2D characters (ThreeCanvas), continuous camera, 2D layers, mixed audio.
import React, {useMemo} from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig, delayRender, continueRender} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {camAt, kickAt, aplicar, type Cam} from './camera';
import {Mundo, HORIZONTE} from './mundo';
import {Personagens} from './personagens';
import {Legenda, Titulo, Contagem, Vinheta, Flash, Velocidade, poseEm} from './camadas';
import {pulso, CONTAGEM} from './dados';

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

export const Video: React.FC = () => {
  const f = useCurrentFrame(), {width, height} = useVideoConfig(), t = f / 30, k = width / 1080;
  const c = camAt(t), [kx, ky] = kickAt(t);
  const cab = /^cab_|lever|desvio/.test(poseEm(t)) || t >= CONTAGEM;
  const bate = cab ? pulso(t) : 0;
  return (
    <AbsoluteFill style={{backgroundColor: HORIZONTE}}>
      <Audio src={staticFile('ep1/audio.wav')} />
      <AbsoluteFill style={{transform: `translate(${kx * k}px, ${ky * k}px) scale(${1.04 + 0.014 * bate})`,
        filter: c.blur > 0.3 ? `blur(${c.blur * k}px)` : undefined}}>
        <ThreeCanvas width={width} height={height} shadows camera={{fov: 38, near: 0.03, far: 4000}} gl={{antialias: true}}>
          <color attach="background" args={[HORIZONTE]} />
          <fog attach="fog" args={[HORIZONTE, 80, 950]} />
          <Rig c={c} />
          <Luzes alvo={c.l} />
          <Mundo t={t} />
          <Personagens t={t} cam={c.p} />
        </ThreeCanvas>
      </AbsoluteFill>
      <Velocidade v={c.linhas} k={k} />
      <Vinheta t={t} />
      <Flash t={t} />
      <Titulo t={t} k={k} />
      <Legenda t={t} k={k} />
      <Contagem t={t} k={k} />
    </AbsoluteFill>
  );
};
