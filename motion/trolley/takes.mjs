// Take bank: renders clean shots (3D world only: no captions, HUD, overlays or audio) of the ACTIVE episode, so later
// episodes reuse them instead of rendering them again. Writes public/takes/<ep>_<name>.mp4 and public/takes/takes.json.
// Usage: node takes.mjs ep2 gancho:0-110,freio:183-392 [-- only these names]
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const [ep, lista] = process.argv.slice(2);
const dir = path.resolve('public/takes');
fs.mkdirSync(dir, {recursive: true});
const manifesto = path.join(dir, 'takes.json');
const bancos = fs.existsSync(manifesto) ? JSON.parse(fs.readFileSync(manifesto, 'utf8')) : {};
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const chromiumOptions = {gl: 'angle'};
const inputProps = {limpo: true};
const composition = await selectComposition({serveUrl, id: 'Video', chromiumOptions, inputProps});
for (const item of lista.split(',')) {
  const [nome, faixa] = item.split(':');
  const [f0, f1] = faixa.split('-').map(Number);
  const clip = `${ep}_${nome}`;
  const t0 = Date.now();
  await renderMedia({serveUrl, composition, codec: 'h264', crf: 14, frameRange: [f0, f1], muted: true, inputProps,
    chromiumOptions, timeoutInMilliseconds: 180000, outputLocation: path.join(dir, `${clip}.mp4`)});
  bancos[clip] = {ep, f0, f1, de: +(f0 / 30).toFixed(3), ate: +((f1 + 1) / 30).toFixed(3)};
  fs.writeFileSync(manifesto, JSON.stringify(bancos, null, 1));
  console.log(`ok ${clip} ${f1 - f0 + 1} quadros em ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}
