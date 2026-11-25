// 2D layers over the 3D picture: giant hook title, coloured word captions, the 10 s countdown with the A/B cards,
// heartbeat vignette, flashes and speed lines. Sizes are in 1080x1920 units and scaled by k = width / 1080.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {PALAVRAS, ROTEIRO, CONTAGEM, DUR, TITULO_ATE, CHAVES, SOLTA, smooth, pulso, rng} from './dados';

const FONTE = 'Preta, "Segoe UI Black", "Arial Black", sans-serif';
const AMARELO = '#FFD60A', AZUL = '#4DB2FF', VERMELHO = '#FF5470', LARANJA = '#FF9A3D';
const GRUPO_A = new Set(['filhotes', 'golden', 'Helena', 'cura', 'câncer', 'fórmula', 'doutora']);
const GRUPO_B = new Set(['Cida', 'panda', 'dona']);
const PERIGO = new Set(['freio', 'quebrar', 'Nada', 'ex', 'dez', 'segundos', 'solta', 'altar']);

const limpa = (w: string) => w.replace(/[.,!?;:]/g, '');
const corDa = (w: string) => { const c = limpa(w);
  if (c === 'A' || GRUPO_A.has(c)) return AZUL; if (c === 'B' || GRUPO_B.has(c)) return VERMELHO; if (PERIGO.has(c)) return LARANJA; return '#ffffff'; };

/** 1-3 words per caption, cut at punctuation or when the speaker changes */
const GRUPOS: number[][] = (() => {
  const out: number[][] = []; let g: number[] = [];
  PALAVRAS.forEach((w, i) => {
    g.push(i);
    const prox = PALAVRAS[i + 1];
    if (g.length === 3 || /[.,!?;:]$/.test(w.w) || !prox || prox.linha !== w.linha) { out.push(g); g = []; }
  });
  return out;
})();

const contorno = (k: number, px: number) => ({WebkitTextStroke: `${px * k}px #111`, paintOrder: 'stroke fill' as const});

export const Legenda: React.FC<{t: number; k: number}> = ({t, k}) => {
  if (t >= CONTAGEM) return null;
  let gi = -1;
  GRUPOS.forEach((g, i) => { if (PALAVRAS[g[0]].a <= t) gi = i; });
  if (gi < 0) return null;
  const g = GRUPOS[gi], fim = Math.min(GRUPOS[gi + 1] ? PALAVRAS[GRUPOS[gi + 1][0]].a : 1e9, PALAVRAS[g[g.length - 1]].b + 0.45);
  if (t > fim) return null;
  const pop = 1 + 0.12 * (1 - smooth((t - PALAVRAS[g[0]].a) / 0.12));
  return (<div style={{position: 'absolute', left: 90 * k, right: 90 * k, top: 1150 * k, textAlign: 'center', lineHeight: 1.05,
    transform: `scale(${pop})`}}>
    {g.map((i) => { const w = PALAVRAS[i], ativa = t >= w.a && t < (PALAVRAS[i + 1]?.a ?? w.b + 0.3);
      return (<span key={i} style={{display: 'inline-block', margin: `0 ${20 * k}px`, fontFamily: FONTE, fontSize: 84 * k,
        color: ativa ? AMARELO : corDa(w.w), transform: `scale(${ativa ? 1.12 : 1})`, ...contorno(k, 14)}}>{w.w.toUpperCase()}</span>); })}
  </div>);
};

export const Titulo: React.FC<{t: number; k: number}> = ({t, k}) => {
  if (t > TITULO_ATE + 0.25) return null;
  const entra = smooth(t / 0.15), sai = smooth((t - TITULO_ATE) / 0.25);
  const s = 1.12 - 0.12 * entra;
  return (<div style={{position: 'absolute', left: 0, right: 0, top: (330 - 500 * sai) * k, textAlign: 'center', opacity: 1 - sai,
    transform: `scale(${s}) rotate(${-3 + 3 * entra}deg)`, fontFamily: FONTE, lineHeight: 0.95}}>
    {ROTEIRO.titulo.split(' ').reduce((l: string[], w, i) => { if (i === 3) l.push(''); l[l.length - 1] = (l[l.length - 1] + ' ' + w).trim(); return l; }, [''])
      .map((linha, i) => (<div key={i} style={{fontSize: (i ? 124 : 104) * k, color: i ? AMARELO : '#fff', ...contorno(k, 20)}}>{linha}</div>))}
  </div>);
};

const Cartao: React.FC<{letra: string; texto: string; cor: string; x: number; k: number; s: number}> = ({letra, texto, cor, x, k, s}) => (
  <div style={{position: 'absolute', left: x * k, top: 860 * k, width: 375 * k, height: 280 * k, background: cor, borderRadius: 34 * k,
    border: `${8 * k}px solid #111`, boxShadow: `0 ${12 * k}px 0 #111`, transform: `scale(${s})`, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 14 * k, boxSizing: 'border-box'}}>
    <div style={{fontFamily: FONTE, fontSize: 130 * k, color: '#fff', lineHeight: 1, ...contorno(k, 12)}}>{letra}</div>
    <div style={{fontFamily: FONTE, fontSize: 34 * k, color: '#fff', lineHeight: 1.1, marginTop: 8 * k, ...contorno(k, 7)}}>{texto}</div>
  </div>);

export const Contagem: React.FC<{t: number; k: number}> = ({t, k}) => {
  const pergunta = PALAVRAS.find((w) => w.linha === 'pergunta')?.a ?? CONTAGEM - 3;
  if (t < pergunta) return null;
  const aparece = smooth((t - pergunta) / 0.3), bate = pulso(t);
  const els: React.ReactNode[] = [
    <Cartao key="a" letra="A" texto={ROTEIRO.trilho_a} cor="#2f86e0" x={120} k={k} s={aparece * (1 + 0.04 * bate)} />,
    <Cartao key="b" letra="B" texto={ROTEIRO.trilho_b} cor="#e0405a" x={515} k={k} s={aparece * (1 + 0.04 * bate)} />,
  ];
  if (t >= CONTAGEM) {
    const dec = t - CONTAGEM, n = Math.max(1, 10 - Math.floor(dec)), u = dec % 1;
    const s = 1 + 0.55 * (1 - smooth(u / 0.18)), cor = n <= 3 ? VERMELHO : '#fff';
    const R = 205, C = 2 * Math.PI * R;
    els.push(<div key="q" style={{position: 'absolute', left: 0, right: 0, top: 300 * k, textAlign: 'center', fontFamily: FONTE, fontSize: 66 * k,
      ...contorno(k, 12)}}><span style={{color: AZUL}}>TRILHO A</span><span style={{color: '#fff'}}> OU </span><span style={{color: VERMELHO}}>TRILHO B?</span></div>);
    els.push(<svg key="r" width={480 * k} height={480 * k} style={{position: 'absolute', left: 300 * k, top: 380 * k}} viewBox="0 0 480 480">
      <circle cx={240} cy={240} r={R} fill="rgba(0,0,0,0.35)" stroke="#111" strokeWidth={30} />
      <circle cx={240} cy={240} r={R} fill="none" stroke={cor} strokeWidth={18} strokeDasharray={`${C * (1 - u)} ${C}`} transform="rotate(-90 240 240)" />
    </svg>);
    els.push(<div key="n" style={{position: 'absolute', left: 0, right: 0, top: 418 * k, textAlign: 'center', fontFamily: FONTE, fontSize: 330 * k,
      lineHeight: 1.18, color: cor, transform: `scale(${s})`, ...contorno(k, 22)}}>{n}</div>);
    els.push(<div key="c" style={{position: 'absolute', left: 0, right: 0, top: 1175 * k, textAlign: 'center', fontFamily: FONTE, fontSize: 58 * k,
      color: AMARELO, transform: `scale(${1 + 0.05 * bate})`, ...contorno(k, 12)}}>COMENTA: A OU B?</div>);
  }
  return <>{els}</>;
};

const CAB = new Set(['cab_ecu', 'cab_mcu', 'cab_shock', 'cab_extreme', 'lever_cu', 'desvio_cu']);
export const poseEm = (t: number) => { let p = CHAVES[0].pose; for (const c of CHAVES) if (c.t <= t) p = c.pose; return p; };

export const Vinheta: React.FC<{t: number}> = ({t}) => {
  const base = t >= CONTAGEM ? 0.5 : CAB.has(poseEm(t)) ? 0.32 : 0.1;
  const a = base * (0.45 + 0.55 * pulso(t));
  return <AbsoluteFill style={{background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 48%, rgba(150,0,0,${a}) 100%)`}} />;
};

export const Flash: React.FC<{t: number}> = ({t}) => {
  const fl: [number, number][] = [[SOLTA, 0.35], [DUR - 0.5, 0.8], ...CHAVES.filter((c) => c.flash).map((c) => [c.t, c.flash!] as [number, number])];
  let a = 0;
  for (const [t0, amp] of fl) if (t >= t0 && t < t0 + 0.3) a = Math.max(a, amp * (1 - (t - t0) / 0.3));
  return a > 0 ? <AbsoluteFill style={{backgroundColor: '#fff', opacity: a}} /> : null;
};

const LINHAS = (() => { const r = rng(9); return Array.from({length: 22}, () => ({a: r() * Math.PI * 2, w: 2 + r() * 5, d: 0.25 + r() * 0.3})); })();
export const Velocidade: React.FC<{v: number; k: number}> = ({v, k}) => (v <= 0.01 ? null : (
  <svg width="100%" height="100%" style={{position: 'absolute', inset: 0}} viewBox="0 0 1080 1920">
    {LINHAS.map((l, i) => { const r0 = 1100 * l.d, r1 = 1300; const cx = 540, cy = 960;
      return <line key={i} x1={cx + Math.cos(l.a) * r0} y1={cy + Math.sin(l.a) * r0} x2={cx + Math.cos(l.a) * r1} y2={cy + Math.sin(l.a) * r1}
        stroke="#fff" strokeWidth={l.w} opacity={v * 0.7} strokeLinecap="round" />; })}
  </svg>));

