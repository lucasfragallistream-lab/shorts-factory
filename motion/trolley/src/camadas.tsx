// 2D layers over the 3D picture: giant hook title, coloured word captions, the 10 s countdown with the A/B cards,
// heartbeat vignette, flashes, speed lines, the distance HUD on the train inserts and the final freeze card. Sizes are in 1080x1920 units and scaled by k = width / 1080.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {PALAVRAS, ROTEIRO, CONTAGEM, TITULO_ATE, CHAVES, SOLTA, CONGELA, FIM_SOM, smooth, pulso, rng, distancia, chaveEm} from './dados';
import {GRUPO_A, GRUPO_B, PERIGO} from './ep3/config';

const FONTE = 'Preta, "Segoe UI Black", "Arial Black", sans-serif';
const AMARELO = '#FFD60A', AZUL = '#4DB2FF', VERMELHO = '#FF5470', LARANJA = '#FF9A3D';

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
  const curto = ROTEIRO.titulo.split(' ').length <= 3;  // a short question title ("QUEM VOCÊ SALVA?") goes giant
  return (<div style={{position: 'absolute', left: 0, right: 0, top: (330 - 500 * sai) * k, textAlign: 'center', opacity: 1 - sai,
    transform: `scale(${s}) rotate(${-3 + 3 * entra}deg)`, fontFamily: FONTE, lineHeight: 0.95}}>
    {ROTEIRO.titulo.split(' ').reduce((l: string[], w, i, ws) => { if (i === Math.min(3, ws.length - 1)) l.push(''); l[l.length - 1] = (l[l.length - 1] + ' ' + w).trim(); return l; }, [''])
      .map((linha, i) => (<div key={i} style={{fontSize: (i ? 124 : 104) * k * (curto ? 1.35 : 1), color: i ? AMARELO : '#fff', ...contorno(k, 20)}}>{linha}</div>))}
  </div>);
};

const Cartao: React.FC<{letra: string; texto: string; cor: string; x: number; k: number; s: number}> = ({letra, texto, cor, x, k, s}) => (
  <div style={{position: 'absolute', left: x * k, top: 235 * k, width: 400 * k, height: 225 * k, background: cor, borderRadius: 30 * k,
    border: `${8 * k}px solid #111`, boxShadow: `0 ${12 * k}px 0 #111`, transform: `scale(${s})`, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 14 * k, boxSizing: 'border-box'}}>
    <div style={{fontFamily: FONTE, fontSize: 96 * k, color: '#fff', lineHeight: 1, ...contorno(k, 11)}}>{letra}</div>
    <div style={{fontFamily: FONTE, fontSize: 33 * k, color: '#fff', lineHeight: 1.1, marginTop: 6 * k, ...contorno(k, 7)}}>{texto}</div>
  </div>);

export const Contagem: React.FC<{t: number; k: number}> = ({t, k}) => {
  const pergunta = PALAVRAS.find((w) => w.linha === 'pergunta')?.a ?? CONTAGEM - 3;
  if (t < pergunta) return null;
  const aparece = smooth((t - pergunta) / 0.3), bate = pulso(t);
  const els: React.ReactNode[] = [
    <Cartao key="a" letra="A" texto={ROTEIRO.trilho_a} cor="#2f86e0" x={100} k={k} s={aparece * (1 + 0.04 * bate)} />,
    <Cartao key="b" letra="B" texto={ROTEIRO.trilho_b} cor="#e0405a" x={580} k={k} s={aparece * (1 + 0.04 * bate)} />,
  ];
  if (t >= CONTAGEM) {
    const dec = t - CONTAGEM, n = Math.max(1, 10 - Math.floor(dec)), u = dec % 1;
    const s = 1 + 0.55 * (1 - smooth(u / 0.18)), cor = n <= 3 ? VERMELHO : '#fff';
    const R = 160, C = 2 * Math.PI * R;
    els.push(<div key="q" style={{position: 'absolute', left: 0, right: 0, top: 140 * k, textAlign: 'center', fontFamily: FONTE, fontSize: 62 * k,
      ...contorno(k, 12)}}><span style={{color: AZUL}}>TRILHO A</span><span style={{color: '#fff'}}> OU </span><span style={{color: VERMELHO}}>TRILHO B?</span></div>);
    els.push(<svg key="r" width={380 * k} height={380 * k} style={{position: 'absolute', left: 350 * k, top: 1100 * k}} viewBox="0 0 380 380">
      <circle cx={190} cy={190} r={R} fill="rgba(0,0,0,0.4)" stroke="#111" strokeWidth={28} />
      <circle cx={190} cy={190} r={R} fill="none" stroke={cor} strokeWidth={17} strokeDasharray={`${C * (1 - u)} ${C}`} transform="rotate(-90 190 190)" />
    </svg>);
    els.push(<div key="n" style={{position: 'absolute', left: 350 * k, width: 380 * k, top: 1100 * k, height: 380 * k, display: 'flex',
      alignItems: 'center', justifyContent: 'center', fontFamily: FONTE, fontSize: 250 * k, lineHeight: 1, color: cor,
      transform: `scale(${s})`, ...contorno(k, 20)}}>{n}</div>);
    els.push(<div key="c" style={{position: 'absolute', left: 0, right: 0, top: 478 * k, textAlign: 'center', fontFamily: FONTE, fontSize: 56 * k,
      color: AMARELO, transform: `scale(${1 + 0.05 * bate})`, ...contorno(k, 12)}}>COMENTA: A OU B?</div>);
  }
  return <>{els}</>;
};

const CAB = /^(cab_|lever|desvio|mao_|olho_)/;
export const poseEm = (t: number) => { let p = CHAVES[0].pose; for (const c of CHAVES) if (c.t <= t) p = c.pose; return p; };

export const Vinheta: React.FC<{t: number}> = ({t}) => {
  const base = t >= CONTAGEM ? 0.5 : CAB.test(poseEm(t)) ? 0.32 : 0.1;
  const a = base * (0.45 + 0.55 * pulso(t));
  return <AbsoluteFill style={{background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 48%, rgba(150,0,0,${a}) 100%)`}} />;
};

export const Flash: React.FC<{t: number}> = ({t}) => {
  const fl: [number, number][] = [[SOLTA, 0.35], ...CHAVES.filter((c) => c.flash).map((c) => [c.t, c.flash!] as [number, number])];
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


/** distance to the switch on the 0.8 s train inserts (the clock is running) */
export const Distancia: React.FC<{t: number; k: number}> = ({t, k}) => {
  const c = chaveEm(t);
  if (c.tag !== 'insert') return null;
  const pop = 1 + 0.25 * (1 - smooth((t - c.t) / 0.12));
  const m = Math.round(distancia(t)).toLocaleString('pt-BR');
  return (<div style={{position: 'absolute', left: 0, right: 0, top: 170 * k, display: 'flex', flexDirection: 'column', alignItems: 'center',
    transform: `scale(${pop})`}}>
    <div style={{background: '#d81f2f', border: `${6 * k}px solid #111`, borderRadius: 18 * k, padding: `${6 * k}px ${26 * k}px`, fontFamily: FONTE,
      fontSize: 40 * k, color: '#fff', ...contorno(k, 6)}}>DISTÂNCIA ATÉ O DESVIO</div>
    <div style={{fontFamily: FONTE, fontSize: 150 * k, lineHeight: 1.05, color: AMARELO, ...contorno(k, 20)}}>{m} m</div>
  </div>);
};

/** final freeze: white/red flashes (at most 3 per second: photosensitivity), then the frame dims in the silence */
export const Congelamento: React.FC<{t: number}> = ({t}) => {
  if (t < CONGELA) return null;
  const fl: [number, string, number][] = [[CONGELA, '#ffffff', 0.85], [CONGELA + 0.34, '#ff1f3d', 0.55], [CONGELA + 0.68, '#ffffff', 0.6]];
  let cor = '#fff', a = 0;
  for (const [t0, c, amp] of fl) if (t >= t0 && t < t0 + 0.26) { const v = amp * (1 - (t - t0) / 0.26); if (v > a) { a = v; cor = c; } }
  const escuro = t >= FIM_SOM ? 0.35 * smooth((t - FIM_SOM) / 0.12) : 0;
  return (<>
    {a > 0 && <AbsoluteFill style={{backgroundColor: cor, opacity: a}} />}
    {escuro > 0 && <AbsoluteFill style={{backgroundColor: '#000', opacity: escuro}} />}
  </>);
};
