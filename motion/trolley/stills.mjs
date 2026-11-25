// Renders a few stills with one bundle (kit: check stills before any render).
// Usage: node stills.mjs out/dir 0,90,300 [Preview|Video]
import {bundle} from '@remotion/bundler';
import {selectComposition, renderStill} from '@remotion/renderer';
import path from 'node:path';

const [dir, lista, comp = 'Preview'] = process.argv.slice(2);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const chromiumOptions = {gl: 'angle'};
const composition = await selectComposition({serveUrl, id: comp, chromiumOptions});
for (const f of lista.split(',').map(Number)) {
  await renderStill({serveUrl, composition, frame: f, chromiumOptions, timeoutInMilliseconds: 180000,
    output: path.resolve(dir, `f${String(f).padStart(4, '0')}.png`)});
  console.log('ok', f);
}
