# shorts-factory

Gera vídeos verticais 1080x1920, 30 fps, exatamente 61,0 s, de rankings ("As 4 crises que você vai viver") com narrador único em pt-BR e personagens genéricos em estilo flat (referência: `docs/referencia_estilo.png`).
Plano completo: `docs/PLANO.md` — leia primeiro a seção 0 (pivô de 20/11/2026). A fase atual está na seção 10. Prompts das fases: `docs/PROMPTS.md` (use os R1 a R6).

## Regras de trabalho
- Uma fase por vez. Ao terminar: rodar `pytest -q`, marcar a seção 10 do plano, parar e resumir em até 5 linhas.
- Custo zero de mídia: nenhuma API paga de voz ou vídeo. A única API é o Gemini (`GEMINI_API_KEY`). Nunca imprima a chave.
  Higgsfield foi testado e descartado em 21/11/2026 (pago por créditos). Sem exceções.
- Só modelos com licença que permita monetizar (ex.: Chatterbox MIT). Nada CC-BY-NC (OmniVoice, XTTS-v2, F5-TTS).
- Só personagens originais e genéricos. Nunca copie personagens, marcas ou o visual de desenhos existentes.

## Economia de tokens
- Conversa em modo `/caveman`. Código, docs e commits em texto normal.
- Rode comandos pela ferramenta Bash (Git Bash), para o hook do rtk agir. Não use a ferramenta PowerShell.
- Saída longa vai para `logs/`. Leia só `tail -n 30` ou `grep -n -i error`.
- FFmpeg sempre com `-hide_banner -loglevel error`; pip com `-q`; pytest com `-q`.
- Não releia arquivo que acabou de escrever. Prefira edições pequenas.
- Revisão visual: um contact sheet PNG por rodada (`tools/contact_sheet.py`, criado na Fase 2), nunca vários frames soltos.
- Não leia `.venv/`, `.venv-tts/`, `motion/node_modules/`, `cache/`, `output/` nem arquivos de mídia.

## Ambiente (Windows + Git Bash)
- Python do projeto: `.venv/Scripts/python.exe` (não dependa de activate).
- `PYTHONUTF8=1`. Caminhos com `pathlib`. `subprocess` sempre com lista de argumentos, sem `shell=True`.
- FFmpeg: `ffmpeg_utils.find_ffmpeg()` procura no PATH e, se não achar, usa `imageio-ffmpeg`.

## Decisões fixas (não rediscutir)
- Estilo: fundo branco, traço escuro limpo, cores chapadas, faixa de título vermelha, etiquetas por item, rótulo amarelo do item atual. Sem textura de papel e sem cenários.
- Composição: Pillow com supersampling 2x → frames RGB por pipe → FFmpeg `h264_nvenc` se disponível, senão `libx264` (`-crf 20`, `-preset veryfast`); sempre `yuv420p` e `+faststart`. Sem MoviePy na composição e sem cairosvg.
- Legendas desenhadas no Pillow: caixa alta, branco com contorno preto grosso, palavra falada em amarelo, dentro da zona segura (plano, seção 4).
- edge-tts: `Communicate(..., boundary="WordBoundary")`. Cache por hash de texto + voz + rate + pitch.
- Narrador único. Voz principal: Chatterbox Multilingual pt-BR (GPU); edge-tts reserva; mock para testes. Timestamps por palavra via faster-whisper quando o motor não os fornece.
- Áudio final: -14 LUFS (medido em EBU R128, ganho exato + limitador -1,5 dB). BGM sempre ligada a -22 dB com `sidechaincompress`: `assets/bgm.mp3` se existir, senão trilha procedural do modo (`bgm.py`).
- Minissérie em fase de aquecimento de conta (21/11/2026): episódios de 30 s (`--duracao 30`, padrão). Voltar a 61 s
  quando for monetizar (roteiros longos guardados como `*_61s.json`).
- Duração: exatamente 61,0 s (1.830 frames), nunca abaixo de 60,0 s. Regras de ajuste no plano, seção 6, item 1.
- Motor de voz plugável: `chatterbox`, `edge` e `mock`.
- Gemini pensa, Claude executa: roteiros, ganchos, CTA e visuais saem de `script_generator.py` (`--tema`, `tools/revisar_rankings.py`), nunca escritos à mão pelo Claude.
- Retenção: todo ranking tem `cta` antes do último item e `visuais` (emoji por palavra falada); a montagem nunca deixa a câmera parada.
- Emojis: fonte local (`assets/fonts/emoji.ttf` ou Segoe UI Emoji do Windows), sem download.

## Definição de pronto (qualquer fase)
- `pytest -q` verde.
- A CLI roda sem traceback. Erros viram mensagem clara e são gravados em `logs/ultimo_erro.txt`.

## Ferramentas instaladas (20/11/2026)
- FFmpeg 9.0 (PATH): cortes, mixagem, encode NVENC.
- Whisper: faster-whisper 1.2.1 em `.venv-tts` (alinhamento de palavras do Chatterbox; `tools/tts_worker.py`).
- yt-dlp: `.venv/Scripts/yt-dlp.exe` (download de referências; respeite direitos autorais, só material que você pode usar).
- HyperFrames 0.9.72 (HeyGen, Apache-2.0): `cd motion && npx hyperframes ...` (HTML → MP4, motion graphics). Teste: `motion/teste`.
- Remotion 4.0.545: `cd motion && npx remotion ...` (React → vídeo). Licença própria: grátis para pessoa física e empresas de até 3 pessoas.
- Uso previsto: aberturas, transições e cartões animados que o Pillow não faz bem; o pipeline principal continua em Pillow + FFmpeg.
