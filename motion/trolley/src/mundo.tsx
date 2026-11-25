// The 3D world (kit: 3D toon world, flat 2D characters): sky, mountains, trees, grass, track with the A/B fork,
// signs, and the steam train with animated wheels, rods, smoke, sparks at the wheels and the cab levers.
// Episode props (box, domino table...) live in src/epN/elenco.tsx.
import React, {useMemo} from 'react';
import * as THREE from 'three';
import {ZF, ramoX, rng, cl, smooth, PUXADAS, SOLTA, CAB_Z, PISO, TRILHO_Y, CONTAGEM, faisca, velocidade} from './dados';

/** kit look: 3-step hard toon ramp */
const RAMP = (() => {
  const d = new Uint8Array([120, 120, 140, 255, 196, 196, 206, 255, 255, 255, 255, 255]);
  const t = new THREE.DataTexture(d, 3, 1, THREE.RGBAFormat);
  t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t;
})();
const cache = new Map<string, THREE.Material>();
export const toon = (cor: string, extra: THREE.MeshToonMaterialParameters = {}) => {
  const k = cor + JSON.stringify(extra);
  if (!cache.has(k)) cache.set(k, new THREE.MeshToonMaterial({color: cor, gradientMap: RAMP, ...extra}));
  return cache.get(k)!;
};
export const HORIZONTE = '#d6e8f4';

const M = (p: [number, number, number], yaw = 0, s: [number, number, number] = [1, 1, 1], rx = 0) =>
  new THREE.Matrix4().compose(new THREE.Vector3(...p), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, yaw, 0)),
    new THREE.Vector3(...s));

const Inst: React.FC<{geo: THREE.BufferGeometry; mat: THREE.Material; ms: THREE.Matrix4[]; cores?: string[];
  sombra?: boolean; recebe?: boolean}> = ({geo, mat, ms, cores, sombra = false, recebe = true}) => {
  const mesh = useMemo(() => {
    const m = new THREE.InstancedMesh(geo, mat, ms.length);
    ms.forEach((x, i) => m.setMatrixAt(i, x));
    if (cores) cores.forEach((c, i) => m.setColorAt(i, new THREE.Color(c)));
    m.instanceMatrix.needsUpdate = true;
    m.castShadow = sombra; m.receiveShadow = recebe; m.frustumCulled = false;
    return m;
  }, [geo, mat, ms, cores, sombra, recebe]);
  return <primitive object={mesh} />;
};

// ---------- sky, ground, mountains, clouds ----------
const Ceu: React.FC = () => {
  const tex = useMemo(() => {
    const c = document.createElement('canvas'); c.width = 4; c.height = 512;
    const g = c.getContext('2d')!, gr = g.createLinearGradient(0, 0, 0, 512);
    gr.addColorStop(0, '#3f7fd6'); gr.addColorStop(0.45, '#8fbdee'); gr.addColorStop(0.5, HORIZONTE); gr.addColorStop(1, HORIZONTE);
    g.fillStyle = gr; g.fillRect(0, 0, 4, 512);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  }, []);
  return (<mesh renderOrder={-1}>
    <sphereGeometry args={[1900, 32, 16]} />
    <meshBasicMaterial map={tex} side={THREE.BackSide} fog={false} depthWrite={false} />
  </mesh>);
};

const Montanhas: React.FC = () => {
  const {ms, cores, neve} = useMemo(() => {
    const r = rng(11), ms: THREE.Matrix4[] = [], cores: string[] = [], neve: THREE.Matrix4[] = [];
    for (let i = 0, n = 0; n < 46 && i < 400; i++) {
      const ang = r() * Math.PI * 2, dist = 520 + r() * 420, h = 140 + r() * 260, w = h * (1.1 + r() * 0.7);
      const x = Math.cos(ang) * dist, z = 600 + Math.sin(ang) * dist * 1.6;
      if (Math.abs(x) - w / 2 < 160 && z > -650) continue;  // keep the valley along the track (and the fork) open
      n++;
      ms.push(M([x, h / 2 - 5, z], r() * 3, [w, h, w])); cores.push(['#6f9a8a', '#7e9fb5', '#5f8f7a', '#8aa8c0'][i % 4]);
      neve.push(M([x, h - h * 0.12, z], r() * 3, [w * 0.25, h * 0.26, w * 0.25]));
    }
    return {ms, cores, neve};
  }, []);
  const cone = useMemo(() => new THREE.ConeGeometry(0.5, 1, 7), []);
  return (<>
    <Inst geo={cone} mat={toon('#ffffff')} ms={ms} cores={cores} recebe={false} />
    <Inst geo={cone} mat={toon('#f4f7fb')} ms={neve} recebe={false} />
  </>);
};

const Nuvens: React.FC = () => {
  const ms = useMemo(() => {
    const r = rng(5), out: THREE.Matrix4[] = [];
    for (let i = 0; i < 40; i++) {
      const x = (r() - 0.5) * 900, y = 110 + r() * 80, z = -600 + r() * 2300;
      for (let j = 0; j < 4; j++) out.push(M([x + (j - 1.5) * 14 + r() * 6, y + r() * 6, z + r() * 10], 0, [18 + r() * 10, 9 + r() * 5, 14]));
    }
    return out;
  }, []);
  const esf = useMemo(() => new THREE.SphereGeometry(1, 12, 8), []);
  return <Inst geo={esf} mat={toon('#ffffff', {fog: false})} ms={ms} recebe={false} />;
};

const Chao: React.FC = () => {
  const {ms, cores} = useMemo(() => {
    const r = rng(3), ms: THREE.Matrix4[] = [], cores: string[] = [];
    for (let i = 0; i < 1800; i++) {
      const z = -260 + r() * 2100, x = (r() - 0.5) * 160, s = 1.5 + r() * 4.5;
      if (Math.abs(x - ramoX(x < 0 ? -1 : 1, z)) < 2.4) continue;
      ms.push(M([x, 0.012, z], r() * 3, [s, 1, s * (0.6 + r() * 0.6)], -Math.PI / 2));
      cores.push(['#74b85c', '#8ccc6a', '#6aa955', '#9ad077'][i % 4]);
    }
    return {ms, cores};
  }, []);
  const disco = useMemo(() => new THREE.CircleGeometry(1, 10), []);
  return (<>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, 0, 400]}>
      <planeGeometry args={[5000, 5000]} />
      <primitive object={toon('#82c262')} attach="material" />
    </mesh>
    <Inst geo={disco} mat={toon('#ffffff')} ms={ms} cores={cores} />
  </>);
};

const Arvores: React.FC = () => {
  const {troncos, copas, bolas, coresC, coresB} = useMemo(() => {
    const r = rng(21), troncos: THREE.Matrix4[] = [], copas: THREE.Matrix4[] = [], bolas: THREE.Matrix4[] = [];
    const coresC: string[] = [], coresB: string[] = [];
    for (let z = -240; z < 1850; z += 4.2) for (const lado of [-1, 1]) {
      if (r() < 0.25) continue;
      const x = lado * (8 + Math.pow(r(), 1.6) * 70);
      if (z < 6 && Math.abs(x) < 13) continue;
      const h = 4 + r() * 5;
      troncos.push(M([x, h * 0.18, z], 0, [0.35, h * 0.36, 0.35]));
      if (r() < 0.6) { copas.push(M([x, h * 0.62, z], r() * 3, [h * 0.42, h * 0.75, h * 0.42])); coresC.push(['#2f7d4f', '#3c8f5a', '#2a6e48'][Math.floor(r() * 3)]); }
      else { bolas.push(M([x, h * 0.62, z], r() * 3, [h * 0.34, h * 0.3, h * 0.34])); coresB.push(['#5aa548', '#6cb84f', '#4f9a44'][Math.floor(r() * 3)]); }
    }
    return {troncos, copas, bolas, coresC, coresB};
  }, []);
  const cil = useMemo(() => new THREE.CylinderGeometry(0.5, 0.6, 1, 6), []);
  const cone = useMemo(() => new THREE.ConeGeometry(1, 1, 8), []);
  const esf = useMemo(() => new THREE.IcosahedronGeometry(1, 1), []);
  return (<>
    <Inst geo={cil} mat={toon('#7a5233')} ms={troncos} sombra />
    <Inst geo={cone} mat={toon('#ffffff')} ms={copas} cores={coresC} sombra />
    <Inst geo={esf} mat={toon('#ffffff')} ms={bolas} cores={coresB} sombra />
  </>);
};

// ---------- track ----------
const Trilhos: React.FC = () => {
  const {dorm, trilhos, lastro} = useMemo(() => {
    const dorm: THREE.Matrix4[] = [], trilhos: THREE.Matrix4[] = [], lastro: THREE.Matrix4[] = [];
    for (let z = 0; z < 1900; z += 0.7) dorm.push(M([0, 0.26, z], 0, [2.6, 0.12, 0.24]));
    for (const s of [-1, 1]) trilhos.push(M([s * 0.72, 0.4, 950], 0, [0.1, 0.16, 1900]));
    lastro.push(M([0, 0.1, 950], 0, [3.6, 0.2, 1900]));
    for (const lado of [-1, 1]) {
      for (let z = 0; z > -260; z -= 0.7) {
        const dx = ramoX(lado, z - 0.35) - ramoX(lado, z + 0.35), yaw = Math.atan2(dx, -0.7);
        dorm.push(M([ramoX(lado, z), 0.26, z], yaw, [2.6, 0.12, 0.24]));
      }
      for (let z = 0; z > -260; z -= 1.0) {
        const x0 = ramoX(lado, z), x1 = ramoX(lado, z - 1), yaw = Math.atan2(x1 - x0, -1), len = Math.hypot(x1 - x0, 1) + 0.03;
        const mx = (x0 + x1) / 2, mz = z - 0.5, cx = Math.cos(yaw), sx = -Math.sin(yaw);
        for (const s of [-1, 1]) trilhos.push(M([mx + s * 0.72 * cx, 0.4, mz + s * 0.72 * sx], yaw, [0.1, 0.16, len]));
        lastro.push(M([mx, 0.1, mz], yaw, [3.4, 0.2, len + 0.05]));
      }
    }
    return {dorm, trilhos, lastro};
  }, []);
  const cubo = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);
  return (<>
    <Inst geo={cubo} mat={toon('#9c9488')} ms={lastro} />
    <Inst geo={cubo} mat={toon('#6b4a32')} ms={dorm} />
    <Inst geo={cubo} mat={toon('#b9bec8')} ms={trilhos} sombra />
  </>);
};

export const Postes: React.FC = () => (<>{[[-8.5, -9], [8.5, -9]].map(([x, z], i) => (
  <mesh key={i} position={[x, 2.6, z]} castShadow><cylinderGeometry args={[0.12, 0.14, 5.2, 8]} /><primitive object={toon('#4a4a52')} attach="material" /></mesh>))}</>);

// ---------- train ----------
const B: React.FC<{p: [number, number, number]; s: [number, number, number]; c: string; r?: [number, number, number]; e?: string}> =
  ({p, s, c, r = [0, 0, 0], e}) => (<mesh position={p} rotation={r} castShadow receiveShadow>
    <boxGeometry args={s} /><primitive object={toon(c, e ? {emissive: e, emissiveIntensity: 0.6} : {})} attach="material" /></mesh>);
const Cil: React.FC<{p: [number, number, number]; r: number; r2?: number; h: number; c: string; rot?: [number, number, number]; seg?: number}> =
  ({p, r, r2, h, c, rot = [0, 0, 0], seg = 20}) => (<mesh position={p} rotation={rot} castShadow receiveShadow>
    <cylinderGeometry args={[r, r2 ?? r, h, seg]} /><primitive object={toon(c)} attach="material" /></mesh>);

const Roda: React.FC<{x: number; y: number; z: number; r: number; ang: number}> = ({x, y, z, r, ang}) => (
  <group position={[x, y, z]} rotation={[ang, 0, 0]}>
    <Cil p={[0, 0, 0]} r={r} h={0.16} c="#b8322a" rot={[0, 0, Math.PI / 2]} />
    <Cil p={[Math.sign(x) * 0.09, 0, 0]} r={r * 0.32} h={0.04} c="#2b2b33" rot={[0, 0, Math.PI / 2]} />
    <B p={[Math.sign(x) * 0.09, 0, 0]} s={[0.03, r * 1.8, 0.1]} c="#e8e2d8" />
    <B p={[Math.sign(x) * 0.09, 0, 0]} s={[0.03, 0.1, r * 1.8]} c="#e8e2d8" />
  </group>);

const Fumaca: React.FC<{t: number}> = ({t}) => {
  const puffs = [];
  for (let k = Math.max(0, Math.floor((t - 2.4) / 0.09)); k <= Math.floor(t / 0.09); k++) {
    const te = k * 0.09, age = t - te; if (age < 0) continue;
    const r = rng(k * 7 + 1);
    const x = (r() - 0.5) * 0.6 + Math.sin(k) * 0.3 * age, y = 4.5 + age * 2.4 + r() * 0.3, z = ZF(te) + 1.4 + age * 1.5;
    const s = 0.45 + age * 1.1;
    puffs.push(<mesh key={k} position={[x, y, z]} scale={[s, s * 0.85, s]}>
      <icosahedronGeometry args={[1, 1]} />
      <meshToonMaterial color="#f4f4f6" gradientMap={RAMP} transparent opacity={cl(1 - age / 2.4) * 0.95} />
    </mesh>);
  }
  return <>{puffs}</>;
};

function alavancaAng(t: number) {
  let a = -0.45;
  for (const p of PUXADAS) { const u = t - p; if (u >= 0 && u < 0.7) a = -0.45 + 1.1 * (u < 0.12 ? smooth(u / 0.12) : 1 - smooth((u - 0.12) / 0.58)); }
  return a;
}

export const Trem: React.FC<{t: number}> = ({t}) => {
  const zf = ZF(t), ang = (ZF(0) - zf) / 0.75, ang2 = (ZF(0) - zf) / 0.42;
  const solta = t >= SOLTA, us = t - SOLTA;
  // the brake handle snaps off: flies up, spins, lands on the cab floor
  const voo = solta ? Math.min(us, 0.75) : 0;
  const hy = solta ? 0.55 + 2.2 * voo - 4.2 * voo * voo : 0, hz = solta ? 0.6 * voo : 0, hr = solta ? -8 * voo : 0;
  return (<group position={[0, 0, zf]}>
    {/* chassis, cowcatcher, boiler, smokebox, bands, chimney, dome, lamp */}
    <B p={[0, 1.25, 4.3]} s={[1.9, 0.5, 8.6]} c="#25252c" />
    <B p={[0, 0.75, -0.15]} s={[2.2, 0.7, 0.8]} c="#b8322a" r={[0.55, 0, 0]} />
    <Cil p={[0, 2.4, 3.3]} r={0.95} h={5.4} c="#2a2c36" rot={[Math.PI / 2, 0, 0]} seg={28} />
    <Cil p={[0, 2.4, 0.55]} r={1.0} h={0.3} c="#1c1d24" rot={[Math.PI / 2, 0, 0]} seg={28} />
    {[1.9, 3.6, 5.2].map((z) => <Cil key={z} p={[0, 2.4, z]} r={0.98} h={0.14} c="#c9a227" rot={[Math.PI / 2, 0, 0]} seg={28} />)}
    <Cil p={[0, 3.75, 1.4]} r={0.22} r2={0.3} h={1.0} c="#1c1d24" />
    <Cil p={[0, 4.3, 1.4]} r={0.38} h={0.16} c="#1c1d24" />
    <mesh position={[0, 3.35, 3.6]} castShadow><sphereGeometry args={[0.45, 16, 12]} /><primitive object={toon('#c9a227')} attach="material" /></mesh>
    <mesh position={[0, 3.05, 0.32]}><sphereGeometry args={[0.24, 16, 12]} /><meshBasicMaterial color="#fff2a8" /></mesh>
    {/* driving wheels + rods, leading wheels */}
    {[2.2, 3.9, 5.6].flatMap((z) => [-1, 1].map((s) => <Roda key={`${z}${s}`} x={s * 1.05} y={1.22} z={z} r={0.75} ang={-ang} />))}
    {[-1, 1].map((s) => <Roda key={`l${s}`} x={s * 1.0} y={0.89} z={0.9} r={0.42} ang={-ang2} />)}
    {[-1, 1].map((s) => <B key={`b${s}`} p={[s * 1.2, 1.22 + 0.38 * Math.sin(-ang), 3.9 + 0.38 * Math.cos(-ang)]} s={[0.07, 0.12, 3.5]} c="#d9d4c8" />)}
    {/* cab: floor, roof, front wall with windows, corner pillars */}
    <B p={[0, PISO - 0.05, 7.3]} s={[2.9, 0.1, 2.7]} c="#5a3b2a" />
    <B p={[0, 4.35, 7.3]} s={[3.2, 0.12, 3.1]} c="#8f1f1a" />
    <B p={[0, 2.25, 6.0]} s={[2.9, 1.4, 0.12]} c="#b8322a" />
    <B p={[0, 4.12, 6.0]} s={[2.9, 0.36, 0.12]} c="#b8322a" />
    {[-1.4, 0, 1.4].map((x) => <B key={x} p={[x, 3.4, 6.0]} s={[0.14, 1.1, 0.12]} c="#b8322a" />)}
    {[-1.4, 1.4].map((x) => <B key={`p${x}`} p={[x, 2.95, 8.6]} s={[0.12, 2.8, 0.12]} c="#b8322a" />)}
    <B p={[0, 2.0, 8.62]} s={[2.9, 0.9, 0.08]} c="#8f1f1a" />
    {/* brake lever (snaps on the third pull) and the yellow switch lever */}
    <group position={[-0.3, PISO + 0.05, 6.5]}>
      <Cil p={[0, 0.1, 0]} r={0.12} h={0.2} c="#2b2b33" />
      {!solta && <group rotation={[alavancaAng(t), 0, 0]}>
        <Cil p={[0, 0.45, 0]} r={0.035} h={0.9} c="#9aa0aa" seg={10} />
        <mesh position={[0, 0.92, 0]}><sphereGeometry args={[0.09, 12, 10]} /><primitive object={toon('#d0302a')} attach="material" /></mesh>
      </group>}
      {solta && <group position={[0.15, Math.max(0.05, hy), hz]} rotation={[hr, 0, us > 0.75 ? Math.PI / 2 : 0]}>
        <Cil p={[0, 0.3, 0]} r={0.035} h={0.6} c="#9aa0aa" seg={10} />
        <mesh position={[0, 0.62, 0]}><sphereGeometry args={[0.09, 12, 10]} /><primitive object={toon('#d0302a')} attach="material" /></mesh>
      </group>}
    </group>
    <group position={[-1.0, PISO + 0.05, 6.9]} rotation={[-0.3 + (t >= CONTAGEM ? 0.05 * Math.sin(t * 31) : 0), 0, 0.03 * Math.sin(t * 23)]}>
      <Cil p={[0, 0.1, 0]} r={0.12} h={0.2} c="#2b2b33" />
      <Cil p={[0, 0.5, 0]} r={0.035} h={1.0} c="#9aa0aa" seg={10} />
      <mesh position={[0, 1.02, 0]}><sphereGeometry args={[0.1, 12, 10]} /><primitive object={toon('#f2c230')} attach="material" /></mesh>
    </group>
    {/* tender + two coaches */}
    <B p={[0, 2.15, 11.2]} s={[2.6, 2.1, 4.4]} c="#2e5e4e" />
    <B p={[0, 3.3, 11.2]} s={[2.3, 0.4, 3.6]} c="#1d1d22" />
    {[0, 1].map((k) => { const z0 = 14 + k * 10.6; return (<group key={k}>
      <B p={[0, 2.45, z0 + 5]} s={[2.8, 2.5, 10]} c="#e8b23a" />
      <B p={[0, 3.85, z0 + 5]} s={[3.0, 0.25, 10.2]} c="#8f1f1a" />
      {[0, 1, 2, 3, 4, 5].flatMap((w) => [-1, 1].map((s) => <B key={`${w}${s}`} p={[s * 1.41, 2.8, z0 + 1 + w * 1.6]} s={[0.03, 0.8, 1.0]} c="#3f5f8a" />))}
      {[1.6, 8.4].flatMap((dz) => [-1, 1].map((s) => <Roda key={`${dz}${s}`} x={s * 1.0} y={0.89} z={z0 + dz} r={0.42} ang={-ang2} />))}
    </group>); })}
  </group>);
};


// ---------- sparks: wheels grinding on the rails (deterministic particles, a function of t) ----------
const EMISSORES: [number, number][] = [[-1, 0.9], [1, 0.9], ...[2.2, 3.9, 5.6].flatMap((z) => [[-1, z], [1, z]] as [number, number][])];
const NF = 420, CICLO = 0.55;
const SEMENTES = (() => { const r = rng(77); return Array.from({length: NF}, (_, i) => ({e: i % EMISSORES.length, fase: r() * CICLO,
  vida: 0.16 + r() * 0.3, vx: 1 + r() * 2.6, vy: 1.2 + r() * 2.8, vz: 4 + r() * 9, h: r(), c: r()})); })();
const Faiscas: React.FC<{t: number}> = ({t}) => {
  const mesh = useMemo(() => {
    const m = new THREE.InstancedMesh(new THREE.BoxGeometry(0.009, 0.009, 1), new THREE.MeshBasicMaterial({color: '#ffffff',
      blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, toneMapped: false}), NF);
    m.frustumCulled = false; return m;
  }, []);
  const o = useMemo(() => new THREE.Object3D(), []), cor = useMemo(() => new THREE.Color(), []);
  const z0 = new THREE.Vector3(0, 0, 1);
  let vivos = 0;
  SEMENTES.forEach((s, i) => {
    const idade = ((t - s.fase) % CICLO + CICLO) % CICLO, tb = t - idade;
    const on = idade < s.vida && s.h < faisca(tb) && tb >= 0;
    if (!on) { o.scale.set(0, 0, 0); o.position.set(0, -50, 0); o.updateMatrix(); mesh.setMatrixAt(i, o.matrix); return; }
    vivos++;
    const [lado, ez] = EMISSORES[s.e], v = velocidade(tb);
    // world position: born at the rail contact, thrown outward/up, streaming back relative to the train
    const x = lado * (0.86 + s.vx * idade), y = 0.47 + s.vy * idade - 4.9 * idade * idade;
    const z = ZF(tb) + ez + (-v + s.vz) * idade;
    const rel = new THREE.Vector3(lado * s.vx, s.vy - 9.8 * idade, s.vz).normalize();
    o.position.set(x, Math.max(0.42, y), z);
    o.quaternion.setFromUnitVectors(z0, rel);
    const k = 1 - idade / s.vida;
    o.scale.set(1, 1, 0.08 + 0.22 * k);
    o.updateMatrix(); mesh.setMatrixAt(i, o.matrix);
    mesh.setColorAt(i, cor.setRGB(1, 0.55 + 0.4 * k * s.c, 0.15 * k));
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  const brilho = faisca(t), zf = ZF(t);
  return (<>
    <primitive object={mesh} />
    {vivos > 0 && brilho > 0.4 && [-1, 1].map((l) => <pointLight key={l} position={[l * 1.1, 0.7, zf + 2.6]} color="#ff9a3d"
      intensity={2.2 * brilho * (0.75 + 0.25 * Math.sin(t * 57 + l))} distance={3} decay={2} />)}
  </>);
};

export const Mundo: React.FC<{t: number}> = ({t}) => (<>
  <Ceu /><Montanhas /><Nuvens /><Chao /><Arvores /><Trilhos /><Postes />
  <Trem t={t} /><Fumaca t={t} /><Faiscas t={t} />
</>);

export {RAMP, CAB_Z, TRILHO_Y};
