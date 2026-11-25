# Prompts das fases (colar no Claude Code)

Antes de cada fase: `/clear` e depois `/caveman`. O Claude Code já carrega o `CLAUDE.md` sozinho.

## Fase 0 — Ambiente

```
Fase 0 do docs/PLANO.md. Confira python, ffmpeg, a GPU (nvidia-smi: marca, VRAM, CUDA; e se o ffmpeg tem h264_nvenc) e se GEMINI_API_KEY existe (nunca mostre a chave). Instale o que faltar (ffmpeg por winget; se falhar, imageio-ffmpeg). Crie a estrutura de pastas da seção 4, o .venv com Python 3.12 e o requirements.txt com versões fixadas. Instale e teste os imports. Grave logs/setup.log terminando em AMBIENTE OK e com a GPU encontrada. Se algo do ambiente mudar, ajuste o CLAUDE.md. Marque a seção 10, pare e resuma.
```

## Fase 1 — Esqueleto, CLI e roteiros de fallback

```
Fase 1 do docs/PLANO.md. Crie config.py, schemas.py (pydantic: Roteiro com titulo, gancho_visual, cenario e falas; Fala com personagem, emocao, texto e zoom_dramatico), ffmpeg_utils.py e main.py com a CLI da seção 7. Crie dois roteiros de fallback em assets/roteiros/ (blackmirror.json e idiota.json), com cerca de 150 palavras cada, mirando 56 a 59 s de fala, usando os 3 personagens e um dos 3 cenários. Escreva testes em tests/. Cumpra o aceite da seção 7. Marque a seção 10, pare e resuma.
```

## Fase 2 — Motor gráfico

```
Fase 2 do docs/PLANO.md. Crie character_renderer.py e scene_renderer.py conforme a seção 4: 3 personagens, 3 expressões, 4 bocas, piscar e 3 cenários, no estilo recorte de papel. Monte os sprites em camadas (corpo, cabeça, olhos, sobrancelhas, boca, cabelo ou chapéu) para animar as partes depois. Use supersampling 2x. Crie tools/contact_sheet.py e gere output/contact_sheet_fase2.png com todos os estados. Me diga só o caminho do PNG. Marque a seção 10 e pare para eu aprovar o visual.
```

## Fase 3 — Voz e lip-sync

```
Fase 3 do docs/PLANO.md. Crie voice_engine.py com os motores edge (edge-tts, WordBoundary, cache) e mock. Liste as vozes pt-BR disponíveis e ajuste o mapa de vozes se precisar. Meça as palavras por segundo de cada personagem e grave em config.py. Implemente o ajuste de duração para 61,0 s (seção 6, item 1), o RMS a 30 fps para boca e pulo, e o timeline.json. Cumpra o aceite da seção 7. Marque a seção 10, pare e me diga o caminho do áudio para eu ouvir.
```

## Fase 4 — Montagem e teste ponta a ponta

```
Fase 4 do docs/PLANO.md. Crie captions.py e video_assembler.py: diretor de câmera, composição, legendas, pipe para FFmpeg, mix com BGM opcional e ducking, e loudnorm. Primeiro gere um clipe de 5 s com voz mock e um contact sheet. Depois gere o episódio completo com edge-tts em output/episodio_teste.mp4. Se der erro, corrija e rode de novo até passar. Confira com ffprobe: 1080x1920, 30 fps, 61,0 s. Marque a seção 10, pare e resuma.
```

> As Fases 5 a 7 abaixo foram substituídas pelo pivô (R1 a R6, no fim deste arquivo).

## Fase 5 — Roteirista Gemini

```
Fase 5 do docs/PLANO.md. Crie script_generator.py com google-genai. Liste os modelos disponíveis na minha chave, escolha um Flash estável e grave em GEMINI_MODEL no config. Escreva os prompts dos modos blackmirror e idiota, com resposta JSON validada pelo schema, checagem de duração (palavras por segundo da Fase 3) com até 2 novas tentativas, e fallback automático. Gere um roteiro de cada modo e um vídeo com: python main.py --modo blackmirror --tema "um aplicativo que avalia o quanto você vale como ser humano". Marque a seção 10, pare e resuma.
```

## Fase 6 — Robustez e qualidade

```
Fase 6 do docs/PLANO.md: tratamento de erros e novas tentativas, desempenho (render em vários processos), overlay opcional de zona segura (--debug-safezone) e README. Gere 3 vídeos seguidos e registre o tempo de render de cada um. Marque a seção 10, pare e resuma.
```

## Fase 7 — Upgrades (escolha um item por vez)

```
Fase 7 do docs/PLANO.md: faça só o item <NOME DO ITEM>. Marque a seção 10, pare e resuma.
```


---

# Pivô para rankings (R1 a R6) — use estes a partir de agora

## R1 — Formato ranking

```
Fase R1 do docs/PLANO.md (leia a seção 0. Pivô). Troque o schema por Ranking (titulo, layout, abertura, itens de 3 a 5 com rotulo, narracao e personagem paramétrico, fechamento). Crie dois rankings de fallback em assets/rankings/ (crises.json, inspirado em docs/referencia_estilo.png, e mais um tema seu), em frases corridas, mirando 56 a 59 s de narração. Ajuste a CLI (--fallback NOME, --ranking ARQ, --tema; remova --modo), o voice_engine (narrador único, timeline com início e fim de cada item) e os testes. Aposente o que for só dos personagens antigos sem quebrar o pipeline de áudio. Cumpra o aceite da R1. Marque a seção 10, pare e resuma.
```

## R2 — Motor gráfico v2

```
Fase R2 do docs/PLANO.md. Veja docs/referencia_estilo.png. Crie figure_renderer.py (personagem paramétrico em camadas, idades de criança a idoso, acessórios, 4 expressões, piscar e boca simples, supersampling 2x, traço limpo e sem textura) e layout_renderer.py (fundo branco, faixa de título vermelha, escada, etiquetas e rótulo amarelo). Gere output/contact_sheet_r2.png com as variações e o layout do ranking crises montado. Me diga só o caminho do PNG. Marque a seção 10 e pare para eu aprovar o visual.
```

## R3 — Narrador Chatterbox pt-BR

```
Fase R3 do docs/PLANO.md. Instale o Chatterbox Multilingual com CUDA (confira a licença do modelo pt-BR e registre no plano) e crie o motor chatterbox no voice_engine, com cache e voz de referência opcional em assets/vozes/narrador.wav. Adicione alinhamento por palavra com faster-whisper para as legendas. Gere a narração do ranking crises com chatterbox e com edge-tts, meça o tempo de geração de cada um e me diga os caminhos dos dois áudios para eu comparar. Cumpra o aceite da R3. Marque a seção 10 e pare.
```

## R4 — Montagem v2

```
Fase R4 do docs/PLANO.md. Adapte o video_assembler ao formato ranking: câmera item a item, destaque da etiqueta e do personagem atual, rótulo amarelo, legendas da narração, música e loudness como hoje. Gere primeiro um clipe de 5 s com voz mock e um contact sheet; depois output/ranking_teste.mp4 com o motor de voz escolhido na R3. Confira com ffprobe: 1080x1920, 30 fps, 61,0 s. Marque a seção 10, pare e resuma.
```

## R5 — Gemini de rankings

```
Fase R5 do docs/PLANO.md. Crie script_generator.py com google-genai gerando Ranking em JSON validado pelo schema. Liste os modelos da minha chave e grave um Flash estável em GEMINI_MODEL. O prompt segue a regra de frases corridas para TTS. Faça a checagem de duração com até 2 novas tentativas e fallback automático. Gere dois rankings e um vídeo com: python main.py --tema "as 5 fases de quem começa a academia". Marque a seção 10, pare e resuma.
```

## R6 — Robustez e novos layouts

```
Fase R6 do docs/PLANO.md. Renderização em vários processos (meça antes e depois), novas tentativas em rede e TTS, README, layouts podio e fila, e modo lote (--lote N). Rode três vídeos seguidos sem intervenção. Marque a seção 10, pare e resuma.
```

## Uso diário (depois da R5)

```
python main.py --tema "as 5 fases de quem começa a academia"
python main.py --fallback top5_fobias
python tools/revisar_rankings.py NOME --gravar
```
