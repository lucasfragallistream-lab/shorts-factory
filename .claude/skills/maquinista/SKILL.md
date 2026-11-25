---
name: maquinista
description: Faz um episódio novo de "Você é o Maquinista" (dilema do bonde, 61 s, vertical, Remotion 3D + personagens 2D, narração pt-BR, contagem A ou B). Use quando pedirem um episódio novo, ajustes de um episódio ou novos dilemas.
---

# Você é o Maquinista — como fazer um episódio

Projeto: `shorts-factory`. Motor: `motion/trolley` (Remotion 4 + three.js). Detalhes e histórico: `docs/PLANO.md`, seção PIVÔ 3.

## Regras do formato
- 61,0 s (1830 quadros, 1080x1920). Fala termina até 50,6 s; contagem "A ou B?" de 51 a 61 s; congela em 59,65 s.
- Narradora em 3ª pessoa, mas o espectador é o maquinista. 3,3–3,9 palavras/s. Claude escreve o roteiro.
- **Gancho**: pergunta gigante ("QUEM VOCÊ SALVA?") desde o quadro 0 até ~3 s, voz desde o quadro 0, 1ª imagem = quem
  está no trilho (rosto chorando), sem entregar a virada. Nada pode sumir aos 2 s sem algo novo entrar.
- Tom de thriller: tremor, ângulo holandês no pânico, inserts de 0,8 s com distância a cada 6–8 s, riser até a virada,
  1 s de silêncio total antes da fala da virada, montagem acelerada na contagem, congelamento com apito → silêncio.
- Dilemas variados (`maquinista/ideias.md`): nada de pessoas, personagens ou marcas reais; nada de sangue.
- Custo zero de mídia; sons só PD/CC0 com créditos; nunca imprimir `GEMINI_API_KEY`.
- Testar com quadros soltos (`node stills.mjs`); render completo só na versão final (é rápido, ~1 min).

## Passo a passo (episódio N)
1. Roteiro `maquinista/epN.json` (`titulo`, `trilho_a`, `trilho_b`, `falas`). Para reaproveitar takes, repita o texto
   das falas genéricas do ep. 2 (`gancho`, `freio1-3`, `divide`, `desvio`, `pergunta`) e use `"atempo": 1.0802`.
2. Voz: `python tools/maquinista_voz.py maquinista/epN.json motion/trolley/src/epN`
3. Sprites: `python tools/maquinista_sprites.py motion/trolley/public/epN/sprites epN` (criar a função `epN`).
4. `src/epN/`: `lugares.ts`, `poses.ts` (POSES_EP), `config.ts` (cores das legendas), `elenco.tsx`, `plano.json`
   (chaves de câmera ancoradas em palavras; `take` + `alinha`/`de` para clipes do banco).
5. Som + eventos: `python tools/maquinista_som.py motion/trolley/src/epN motion/trolley/public/epN`
6. Trocar `epX` → `epN` nos imports de `dados.ts`, `camera.ts`, `camadas.tsx`, `Video.tsx`.
7. Conferir: `node stills.mjs out/dir 0,45,...` → folha de contato; corrigir poses.
8. Render: `npx remotion render src/index.ts Video ../../output/maquinista/epN_maquinista.mp4 --gl=angle`
   Conferir folha a cada 0,5 s, -14 LUFS, `pytest -q`. Cópia leve: ffmpeg `-crf 25`.

## Banco de takes (economia)
- `node takes.mjs ep2 nome:f0-f1,...` renderiza trechos LIMPOS (sem legenda/HUD) em `public/takes/` + `takes.json`.
- Vídeos finais têm legenda gravada: só take limpo serve para reaproveitar.
- Já existem: `ep2_gancho`, `ep2_freio`, `ep2_insert_roda`, `ep2_insert_trilho`, `ep2_desvio`, `ep2_contagem`.
