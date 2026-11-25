# Shorts Factory — Análise e Plano de Execução

Criado em 19/11/2026. Este documento é a fonte da verdade do projeto. Em uma conversa nova, leia primeiro a seção **0. Pivô**, depois a seção **10. Status** e a fase atual.

---

## 0. Pivô para rankings (decidido em 20/11/2026) — LEIA PRIMEIRO

Depois da Fase 4, o formato mudou. Esta seção vale mais que as seções 4 a 7 onde elas conflitarem.

**Formato novo:** vídeos de ranking com narrador único: "As 4 crises que você vai viver", "Os 5 mais...", "As 3 coisas que...". Cada vídeo apresenta N itens (3 a 5), um de cada vez, com abertura e fechamento.

**Estilo visual novo** (referência: `docs/referencia_estilo.png`):
- Fundo branco ou quase branco, traço escuro limpo, cores chapadas, sombra suave. Sem textura de papel e sem cenários.
- Título em faixa vermelha inclinada, letras brancas grossas com contorno, no topo.
- Personagens genéricos e paramétricos, um por item: idade (criança, adolescente, jovem adulto, adulto, meia-idade, idoso), cabelo, cor de pele, roupa, acessórios (óculos, barba, caneca, mochila, moletom, gravata).
- Etiqueta branca com borda sobre cada personagem ("13 anos"). O item atual fica em destaque: etiqueta azul, câmera aproximando, e rótulo amarelo grande embaixo.
- Layouts de ranking: `escada` (progressão, como na referência), `podio` (top 3) e `fila` (lado a lado). A v1 começa pela `escada`.
- Os personagens no estilo South Park (Rogério, Jurandir, Dona Sônia) e os 3 cenários foram aposentados.

**Voz:**
- Narrador único com Chatterbox Multilingual, modelo pt-BR, licença MIT (pode monetizar), na RTX 3060. Voz clonada de 5 a 10 s de uma gravação de referência que você tenha direito de usar, ou a voz padrão do modelo.
- O Chatterbox não devolve timestamps por palavra. Por isso a legenda usa alinhamento forçado com faster-whisper (MIT) no áudio gerado.
- edge-tts continua como reserva e `mock` para testes.
- voicestudio avaliado e descartado como padrão: o modelo padrão (OmniVoice) tem pesos CC-BY-NC, sem uso comercial; pt-BR não confirmado; sem timestamps por palavra na API. Pode voltar como motor plugável se aparecer um modelo comercial com bom pt-BR.

**Regras de retenção (pedido do usuário em 20/11/2026):** a tela nunca fica parada — cada item tem 2 ou 3 emojis ligados a palavras faladas (`visuais`), com punch-in no rosto e zoom de volta; antes do último item vem o `cta` (seguir, curtir e comentar se concorda com o ranking). O Gemini faz o trabalho criativo (roteiro, gancho, CTA, visuais); o Claude Code só executa.

**Mantido:** 61,0 s exatos (1.830 quadros), 1080x1920, 30 fps, NVENC, -14 LUFS, música de fundo sempre ligada, legendas dinâmicas na zona segura, cache, logs, Gemini como roteirista. Um tom só, leve e identificável, como na referência; os modos `blackmirror` e `idiota` saem.

**Reaproveitado da v1:** `config.py`, `ffmpeg_utils.py`, `main.py` (CLI), o motor plugável, o ajuste de duração e o timeline de `voice_engine.py`, `captions.py`, `bgm.py`, a mixagem e o encode de `video_assembler.py`, e `tools/contact_sheet.py`. **Refeito:** `schemas.py` (Ranking), os personagens (novo renderizador), o layout e a câmera (item a item), e os roteiros de fallback.

---

## 1. Resumo

- Pipeline local e gratuito: Gemini (roteiro, sua chave) → edge-tts (voz e timestamps por palavra) → Pillow (personagens e cenários em recorte de papel) → lip-sync por RMS → compositor Python com FFmpeg → MP4 1080x1920, 30 fps.
- Execução em 8 fases curtas. Cada fase tem uma entrega testável e um ponto de checagem.
- **Execução (decidido em 19/11):** o Claude Code roda localmente no seu Windows, dentro de `C:\fabricadevideo\shorts-factory`, com caveman e rtk instalados. Ele lê o `CLAUDE.md` e este plano, e executa uma fase por vez com os prompts de `docs\PROMPTS.md`.
- **Duração (decidido em 19/11):** exatamente 61,0 s (1.830 frames), para entrar no TikTok Creator Rewards (mínimo de 1 minuto) e continuar válido em Shorts e Reels.

---

## 2. Diagnóstico do ambiente (19/11/2026)

| Item | Resultado | Consequência |
|---|---|---|
| Pasta `C:\fabricadevideo` | Conectada e vazia | O projeto nasce do zero em `C:\fabricadevideo\shorts-factory` |
| Shell do Claude (chat) na sua máquina | Falhou ao iniciar | Por isso a execução vai para o Claude Code local |
| Nuvem do Claude (chat) | Servidor de voz da Microsoft, Hugging Face e API Gemini bloqueados | A nuvem não serve para o teste real; tudo roda no seu PC |
| Seu Windows | Tem GPU (confirmado em 19/11); Python, FFmpeg, modelo e VRAM ainda desconhecidos | A Fase 0 confere com `nvidia-smi`. Se for NVIDIA: codificação por NVENC e vozes com emoção na GPU |

---

## 3. Economia de tokens

### Ferramentas

**caveman** (MIT/Apache-2.0, github.com/JuliusBrussee/caveman)
- Faz o agente responder de forma curta e sem enrolação, preservando código, comandos e erros.
- Ganho medido pelo autor: cerca de 33% menos tokens de entrada em sessões do Claude Code; na saída, o ganho é pequeno contra um simples "seja conciso", e maior no modo `/ultracave`.
- No claude.ai: skill proposta nesta conversa (ativar com `/caveman`).
- No Claude Code do Windows (parte do setup): plugin `caveman@caveman`, ligado em toda sessão com `/caveman`. A CLI do caveman envia estatísticas de uso por padrão; o setup define `DO_NOT_TRACK=1`.
- Regra do próprio caveman: código, documentos e commits continuam em texto normal; só a conversa é comprimida.

**rtk — Rust Token Killer** (Apache-2.0, github.com/rtk-ai/rtk)
- Proxy de linha de comando que filtra e comprime a saída de comandos (git, pytest, ls, grep etc.) antes de ela chegar ao modelo.
- No Claude Code do Windows (parte do setup): `winget install rtk-ai.rtk` e depois `rtk init -g` (versão 0.37.2 ou mais nova já instala o hook nativo do Windows). Confira com `rtk gain`. Não use `cargo install rtk` do crates.io: esse nome instala outro projeto.
- Limite: o hook só age em comandos de shell, não nas ferramentas Read/Grep internas.
- **Atenção no Windows:** o hook do rtk só intercepta a ferramenta `Bash` do Claude Code. Com o Git for Windows instalado, o Claude Code também ativa a ferramenta PowerShell, que passa por fora do rtk. Por isso o setup instala o Git for Windows e define `CLAUDE_CODE_USE_POWERSHELL_TOOL=0`, para todos os comandos irem pelo Bash. Detalhes em `docs\SETUP_WINDOWS.md`.

### Regras práticas (valem mais que as ferramentas)

1. Logs vão para arquivo. O Claude lê só o final ou as linhas de erro. FFmpeg roda com `-loglevel error` e pip com `-q`.
2. Inspeção visual por uma única imagem "contact sheet" com várias miniaturas por rodada, nunca frame a frame.
3. Edições pequenas por diff. Nenhum arquivo é reescrito inteiro sem necessidade, e arquivo recém-escrito não é relido.
4. Testes com saída curta (`pytest -q`).
5. Este documento evita que uma conversa nova redescubra o projeto.
6. O roteiro usa o Gemini (sua cota), não o Claude.
7. Cache de áudio por hash de texto+voz e cache de sprites: nada é gerado duas vezes.

---

## 4. Arquitetura

### Fluxo

```
main.py (CLI)
  └─ script_generator.py   Gemini (JSON com schema) ou roteiro local de fallback
       └─ roteiro.json
  └─ voice_engine.py       edge-tts por fala → mp3 → wav
                           WordBoundary → timestamps por palavra
                           RMS a 30 fps → boca e pulo do corpo
       └─ timeline.json
  └─ video_assembler.py    diretor de câmera + compositor Pillow + legendas
                           frames RGB → pipe → FFmpeg (libx264)
                           mix: voz + BGM -22 dB com ducking + loudnorm
       └─ output/episodio_*.mp4
```

### Estrutura de pastas

```
C:\fabricadevideo\shorts-factory\
  main.py                orquestrador CLI
  config.py              constantes (1080x1920, 30 fps), caminhos, mapa personagem → voz
  schemas.py             Roteiro e Fala (pydantic) com validação
  script_generator.py    Gemini + fallback
  character_renderer.py  personagens, expressões, bocas
  scene_renderer.py      3 cenários
  voice_engine.py        TTS, timestamps, RMS, lip-sync
  captions.py            legendas dinâmicas
  video_assembler.py     câmera, composição, FFmpeg, mix de áudio
  ffmpeg_utils.py        localizar FFmpeg (PATH ou imageio-ffmpeg) e rodar com log
  assets\fonts\  assets\roteiros\  assets\bgm.mp3 (opcional)
  cache\  output\  logs\  tests\
  docs\PLANO.md  docs\PROMPTS.md  docs\SETUP_WINDOWS.md
  requirements.txt  README.md  CLAUDE.md  .venv\
```

### Decisões técnicas

| Decisão | Motivo |
|---|---|
| FFmpeg por subprocess, com frames enviados por pipe (sem MoviePy na composição) | Composição frame a frame no MoviePy é lenta e acrescenta dependências; o pipe é mais rápido e controlável |
| Pillow com supersampling 2x (sem cairosvg) | cairosvg precisa da DLL do Cairo no Windows, fonte comum de erro de instalação |
| Legendas desenhadas no Pillow (sem ASS/libass) | Não depende de como o FFmpeg foi compilado |
| edge-tts com `boundary="WordBoundary"` | Nas versões 7.x o padrão passou a ser SentenceBoundary; sem isso não vêm timestamps por palavra |
| Gemini pelo SDK `google-genai`, com saída JSON e schema | O modelo fica em `GEMINI_MODEL`, escolhido na Fase 5 a partir da lista de modelos da sua chave |
| Áudio final em -14 LUFS (loudnorm); BGM a -22 dB com `sidechaincompress` | Volume padrão das plataformas; a música abaixa sozinha quando alguém fala |
| Motor de voz plugável (`edge`, `mock`, depois `kokoro`, `piper`, `chatterbox`) | Testes offline e plano B caso o edge-tts pare |

### Personagens (originais, sem copiar South Park)

| Arquétipo | Visual | Voz inicial (validar na Fase 3) |
|---|---|---|
| O Cético — "Rogério" | Óculos, cabelo castanho liso, blusa verde | `pt-BR-AntonioNeural`, rate -5%, pitch -4Hz |
| O Conspiracionista — "Jurandir" | Chapéu de papel-alumínio, olhos arregalados, jaqueta laranja | `pt-BR-AntonioNeural`, rate +18%, pitch +12Hz (ou voz multilíngue) |
| A Chefe — "Dona Sônia" | Coque grisalho, terninho roxo, colar | `pt-BR-FranciscaNeural`, rate 0%, pitch -6Hz |

- Estilo: formas geométricas simples, cores chapadas, contorno escuro, sombra de recorte, textura leve de papel, olhos ovais grandes e juntos, mãos sem dedos.
- Expressões: normal, bravo, chocado. Bocas: fechada, semi_aberta, aberta, formato_o. Piscar automático.
- `pt-BR-ThalitaNeural` fica reservada para uma quarta personagem ou narradora.
- Cenários: sala de estar, beco escuro à noite, escritório corporativo.

### Lip-sync e movimento

- RMS por frame (janela de 1/30 s), normalizado por fala e suavizado (cada boca dura no mínimo 2 frames, para não piscar).
- Faixas iniciais: abaixo de 0,12 → fechada; abaixo de 0,40 → semi_aberta; a partir de 0,40 → aberta. `formato_o` quando a palavra ativa (pelo timestamp do edge-tts) tem O/U dominante.
- Quem fala: pulo vertical proporcional ao volume, rotação leve de ±2°, squash & stretch.
- Quem escuta: respiração, piscadas e reação de expressão quando alguém grita.

### Câmera

- 0–2 s (`gancho_visual`): punch-in rápido, tremor e texto de gancho grande.
- Troca de quem fala → corte para close (~1,6x) em quem fala.
- A cada 3 falas, ou em fala longa → plano geral.
- `zoom_dramatico: true` → aproximação lenta de 1,3x a 2,0x com easing durante a fala.
- Cortes secos, no estilo do desenho.

### Legendas

- Blocos de 2 a 4 palavras, caixa alta, fonte bold/black, texto branco com contorno preto grosso, palavra falada em amarelo com um leve "pop".
- Zona segura: centro da legenda a cerca de 62% da altura; margens laterais de 90 px; fora dos 380 px inferiores e dos 140 px da direita (botões do TikTok/Reels).

---

## 5. Alternativas gratuitas pesquisadas

### Voz (substitutos do ElevenLabs)

| Motor | Onde roda | pt-BR | Clonagem / emoção | Uso comercial | Papel no projeto |
|---|---|---|---|---|---|
| edge-tts | Online (servidor da Microsoft) | Sim (Antonio, Francisca, Thalita) | Não; só pitch e rate | Serviço não oficial: zona cinzenta e pode parar | Padrão da v1 |
| Kokoro-82M | CPU | Sim (poucas vozes) | Não | Apache-2.0 | Plano B offline |
| Piper | CPU, muito leve | Sim (ex.: faber) | Não | Motor GPL; licença varia por voz (ver model card) | Plano B offline |
| Chatterbox Multilingual V3 (Resemble AI) | GPU (CPU lento) | Sim, com modelo dedicado pt-BR | Clona com 5–10 s de áudio; controle de emoção | MIT | Upgrade "ElevenLabs grátis" se houver GPU NVIDIA |
| Qwen3-TTS (Alibaba) | GPU (4–6 GB de VRAM ou mais) | Português | Clona com 3 s; cria voz por descrição | Apache-2.0 | Upgrade alternativo |
| Pocket TTS (Kyutai) | CPU | Português (variante a confirmar) | Clonagem local | Pesos CC BY 4.0 (exige atribuição) | Candidato a testar |

Evitar para monetização: XTTS-v2 e F5-TTS, porque os pesos não permitem uso comercial.

### Animação

- **Rhubarb Lip Sync** (MIT, executável para Windows): o reconhecedor fonético funciona em qualquer idioma e gera 6 a 9 formas de boca, que mapeamos para as nossas 4 (ou ampliamos). Entra na Fase 7.
- **Movimento procedural próprio** (easing, squash & stretch, respiração, piscar, tremor de câmera): sem dependências e com controle total. Entra na v1.
- Descartados: Live2D e Spine (pagos), Blender e Synfig (pesados para automação), MoviePy para composição (lento).

---

## 6. Riscos e decisões

1. **Duração e monetização (decidido: 61,0 s).** A spec pedia 45–58 s, mas o TikTok Creator Rewards só paga vídeos com 1 minuto ou mais. Como chegar a exatamente 61,0 s sem cortar fala:
   - O roteiro mira 56–59 s de fala. A taxa real de palavras por segundo de cada voz é medida na Fase 3 e usada pelo roteirista.
   - Se o áudio ficar curto: as pausas entre falas aumentam (até +0,3 s cada) e o final ganha um "respiro" de reação até completar 61,0 s.
   - Se ficar longo: as pausas diminuem, depois a fala é acelerada até 8% (`atempo`); se ainda passar, o Gemini encurta o roteiro.
   - Trava: o vídeo nunca sai com menos de 60,0 s. `--duracao` continua configurável.
2. **Políticas do YouTube.** Conteúdo produzido em massa e repetitivo não é monetizado ("conteúdo inautêntico"). A atualização de julho de 2026 também tirou a monetização de vídeos angustiantes ou manipuladores. Na prática: variar formatos, revisar antes de publicar e manter o modo blackmirror perturbador, sem choque gráfico.
3. **edge-tts.** Usa um serviço não oficial, sem permissão clara de uso comercial, que pode parar. Mitigação: motor de voz plugável com alternativa offline.
4. **Só uma voz masculina pt-BR no Edge.** Diferenciar por pitch e rate ou usar vozes multilíngues (com sotaque). Validar a lista na Fase 3.
5. **Propriedade intelectual.** Só personagens originais, sem nomes, logotipo ou visual de South Park.
6. **Shell do Claude (chat) indisponível no seu PC.** Resolvido: a execução fica com o Claude Code local.
7. **GPU.** Você tem GPU. As vozes com clonagem e emoção (Chatterbox, Qwen3-TTS) e o NVENC dependem de placa NVIDIA com CUDA. Em placa AMD ou Intel, continuamos com edge-tts e motores de CPU. A Fase 0 confirma marca e VRAM.

---

## 7. Plano de execução por fases

Legenda de custo: 🟢 baixo · 🟡 médio · 🔴 alto (em tokens do Claude).

### Fase 0 — Ambiente 🟢
- Você: segue `docs\SETUP_WINDOWS.md` (Git, Python 3.12, FFmpeg, rtk, Claude Code, caveman) e abre o Claude Code na pasta do projeto.
- Claude Code: confere `python`, `ffmpeg`, `nvidia-smi` e `GEMINI_API_KEY`; instala o que faltar (FFmpeg por winget ou, se falhar, `imageio-ffmpeg`); cria a estrutura de pastas, o `.venv` e o `requirements.txt`; testa os imports.
- Registrar a GPU: marca, VRAM, versão do CUDA (`nvidia-smi`) e se o FFmpeg tem `h264_nvenc` (`ffmpeg -hide_banner -encoders`).
- Aceite: `logs\setup.log` termina com `AMBIENTE OK` e registra a GPU encontrada.

### Fase 1 — Esqueleto, CLI e roteiros de fallback 🟢
- `main.py` com `--modo {blackmirror,idiota}`, `--tema`, `--fallback`, `--duracao`, `--tts {edge,mock}`, `--saida`, `--seed`, `--sem-bgm`.
- `config.py`, `schemas.py` e dois roteiros de exemplo (um por modo), validados pelo schema.
- Aceite: `python main.py --modo idiota --fallback --somente-validar` passa; `pytest -q` verde.

### Fase 2 — Motor gráfico 🟡
- 3 personagens × 3 expressões × 4 bocas, mais piscar; 3 cenários; textura de papel e sombra de recorte.
- Entrega: um contact sheet PNG para você aprovar o visual. **Ponto de decisão: estilo.**
- Aceite: você aprova ou pede ajustes de cor e forma.

### Fase 3 — Voz e lip-sync 🟡
- edge-tts por fala, com voz, pitch e rate por personagem; timestamps WordBoundary; cache; conversão para wav; RMS a 30 fps → boca e pulo; `timeline.json`.
- Motor mock para testes rápidos sem rede.
- Medir a taxa real de palavras por segundo de cada voz e gravar em `config.py` (usada para mirar 61,0 s).
- Ajuste de duração: pausas, "respiro" final e `atempo` até 8%, com trava de 60,0 s.
- Aceite: `python main.py --fallback --so-audio` gera áudio de exatamente 61,0 s e a timeline, e você ouve uma amostra.

### Fase 4 — Montagem e teste ponta a ponta 🟡 (marco principal da spec)
- Diretor de câmera, compositor, legendas, pipe para FFmpeg, mix com BGM opcional e ducking, loudnorm.
- Codificação: `h264_nvenc` se a Fase 0 encontrar NVENC; senão `libx264`. Escolha automática, com `--encoder` para forçar.
- Primeiro um clipe curto com voz mock e um contact sheet dos quadros-chave; depois o episódio completo com edge-tts.
- `python main.py --modo idiota --fallback --saida output\episodio_teste.mp4`. Em caso de erro, o Claude Code lê `logs\ultimo_erro.txt` e corrige até passar.
- Aceite: arquivo 1080x1920, 30 fps, 61,0 s (conferido com `ffprobe`), com áudio sincronizado.

### Fase 5 — Roteirista Gemini 🟢
- Prompts dos dois modos (gancho em 2 s, escalada, reviravolta ou caos), schema JSON, checagem de duração com nova tentativa e fallback automático.
- Regra de escrita para TTS (aprendida na Fase 3): frases corridas, sem enumerações com vírgula ("sentado, trabalhando, respirando"), sem siglas ("RH" → "departamento pessoal") e sem sequências de frases de 2 ou 3 palavras. O edge-tts faz pausas artificiais nesses pontos e a fala soa robótica.
- Reserva opcional compatível com OpenAI (variáveis `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_MODEL`). Ordem: Gemini → reserva (se configurada) → roteiro local. Serve para apontar depois para o FreeLLMAPI ou para um provedor gratuito, sem mudar código.
- Aceite: dois roteiros reais (um por modo) e um vídeo com um tema seu.

### Fase 6 — Robustez e qualidade 🟡
- Erros e novas tentativas (rede, TTS), logs, desempenho (renderização em vários processos), sobreposição opcional da zona segura para conferência, README.
- Aceite: três vídeos seguidos sem intervenção, com tempo de render medido.

### Fase 7 — Upgrades gratuitos (opcional, você escolhe) 🟡/🔴
- **Prioridade 1 (se a GPU for NVIDIA): voz com emoção na GPU.** Motor `chatterbox` com o modelo pt-BR do Chatterbox Multilingual V3 (MIT). O campo `emocao` do roteiro (normal, bravo, chocado) controla a intensidade da fala. Cada personagem ganha uma voz própria, clonada de 5 a 10 s de uma gravação de referência que você tenha direito de usar (sua voz, de um amigo com autorização ou de banco livre). Isso resolve o risco 4 (só uma voz masculina no Edge). Qwen3-TTS (Apache-2.0) fica como alternativa: ele cria voz a partir de uma descrição em texto. Teste: comparar o mesmo roteiro com edge-tts e chatterbox, medir o tempo de geração e decidir o padrão.
- Depois: Rhubarb (bocas por fonema), Kokoro ou Piper offline, novos personagens e cenários, títulos e hashtags automáticos, modo lote.

---

### Fases do pivô (R1 a R6) — substituem as Fases 5 a 7 originais

### R1 — Formato ranking: schema, roteiros e CLI 🟢
- `schemas.py`: `Ranking` com `titulo` (faixa do topo), `layout` (`escada`, `podio`, `fila`), `abertura` (narração), `itens` (3 a 5) e `fechamento`. Cada `Item` tem `rotulo` ("13 anos"), `narracao` e `personagem` (idade, sexo, pele, cabelo, cor da roupa, acessórios, expressão).
- Dois rankings de fallback em `assets/rankings/`, em frases corridas (regra de TTS da Fase 5), mirando 56 a 59 s de narração.
- CLI: `--ranking ARQ`, `--fallback NOME`, `--tema`; saem `--modo` e os modos antigos. O timeline ganha a marcação de início e fim de cada item.
- Aceite: `python main.py --fallback crises --somente-validar` e `pytest -q` verdes.

### R2 — Motor gráfico v2 (estilo da referência) 🟡
- `figure_renderer.py`: personagem paramétrico em camadas (corpo, cabeça, cabelo, rosto, roupa, acessórios), expressões (feliz, preocupado, cansado, chocado), piscar, boca simples. Supersampling 2x, traço limpo, sem textura.
- `layout_renderer.py`: fundo branco, faixa de título vermelha, escada, etiquetas e rótulo inferior amarelo.
- Entrega: `output/contact_sheet_r2.png` com variações de idade e acessórios e o layout montado. **Ponto de decisão: estilo.**

### R3 — Narrador Chatterbox pt-BR 🟡
- Instalar o Chatterbox Multilingual com CUDA no `.venv` (ou em `.venv-tts` separado, se houver conflito de versões) e conferir a licença do modelo pt-BR.
- Motor `chatterbox` no `voice_engine.py`, com cache e voz de referência em `assets/vozes/narrador.wav` (opcional).
- Alinhamento por palavra com faster-whisper (CUDA) para as legendas.
- Comparar a mesma narração com chatterbox e edge-tts e medir o tempo de geração. Você escolhe o padrão ouvindo.
- Aceite: `python main.py --fallback crises --so-audio --tts chatterbox` gera 61,000 s com o timeline por palavra.

### R4 — Montagem v2 e teste ponta a ponta 🟡
- Câmera por item: plano geral na abertura (título + todos os itens), aproximação no item atual com a etiqueta destacada, revelação progressiva (opcional) e plano geral no fechamento.
- Animação: o personagem do item atual quica de leve e reage; os outros respiram e piscam.
- Legendas da narração (as de hoje) e rótulo amarelo do item atual.
- Aceite: `output/ranking_teste.mp4` com 1080x1920, 30 fps e 61,0 s, conferido com ffprobe; contact sheet dos quadros-chave.

### R5 — Roteirista Gemini de rankings 🟢
- Igual à antiga Fase 5, gerando `Ranking` em JSON: título no formato "As N ... que ...", itens com rótulo, narração em frases corridas e descrição do personagem. Checagem de duração com até 2 novas tentativas e fallback.
- Aceite: dois rankings reais e um vídeo com um tema seu.

### R6 — Robustez, desempenho e novos layouts 🟡
- Renderização em vários processos, novas tentativas, README, layouts `podio` e `fila`, e lote de vídeos.

---

## 8. Como cada fase roda

1. Abra o Claude Code em `C:\fabricadevideo\shorts-factory` (ele carrega o `CLAUDE.md` sozinho).
2. Digite `/caveman` e cole o prompt da fase, de `docs\PROMPTS.md`.
3. O Claude Code escreve o código, roda os testes, corrige os erros e grava os logs em `logs\`.
4. No fim da fase ele marca a seção **10. Status** deste documento e para, esperando você.
5. Revise a entrega (no caso da Fase 2, o contact sheet) e cole o prompt da próxima fase. Use `/clear` entre fases para não carregar o histórico antigo.

Cópia do plano no projeto do claude.ai (VÍDEOS): `claude/PLANO.md`. Se mudar algo importante, atualize as duas cópias.

---

## 9. Fontes principais

- caveman: https://github.com/JuliusBrussee/caveman
- rtk: https://github.com/rtk-ai/rtk
- Chatterbox: https://www.resemble.ai/learn/models/chatterbox-multilingual
- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS
- Rhubarb Lip Sync: https://github.com/DanielSWolf/rhubarb-lip-sync
- Comparativo de TTS 2026: https://micdrop.dev/blog/top-open-source-text-to-speech-models

---

## 10. Status

- [x] Análise e plano (19/11/2026)
- [x] Fase 0 — Ambiente (20/11/2026: RTX 3060 12 GB, CUDA 13.4, h264_nvenc ok)
- [x] Fase 1 — Esqueleto e CLI (20/11/2026: 32 testes verdes; pps por personagem ainda estimado)
- [x] Fase 2 — Motor gráfico (20/11/2026: contact sheet em output/contact_sheet_fase2.png; visual aprovado em 20/11/2026)
- [x] Fase 3 — Voz e lip-sync (20/11/2026: áudio de 61,000 s em output/episodio_idiota_voz.wav; pt-BR no Edge: Antonio, Francisca, ThalitaMultilingual — mapa mantido; palavras/s medidas: Rogério 2,04, Jurandir 3,03, Sônia 3,02; roteiros ajustados para 56–59 s de fala; idiota aprovado de ouvido; blackmirror reescrito em frases corridas após soar robótico e aprovado de ouvido)
- [x] Fase 4 — Teste ponta a ponta (20/11/2026: `output/episodio_teste.mp4` 1080x1920, 30 fps, 61,000 s, 1830 quadros, h264_nvenc, -14,0 LUFS, pico -1,5 dB; render 145 s; clipe mock `output/clipe_mock.mp4`; contact sheet `output/contact_sheet_fase4.png`; BGM sempre ligada — trilha procedural por modo quando não há `assets/bgm.mp3`; aprovado em 20/11/2026)
- [~] Fases 5 a 7 originais — substituídas pelo pivô (seção 0)
- [x] Pivô para rankings planejado (20/11/2026: narrador único, Chatterbox pt-BR, 61 s, um tom só, estilo de `docs/referencia_estilo.png`)
- [x] R1 — Formato ranking (20/11/2026: schema Ranking/Item/Personagem; fallbacks crises e salario com ~177 palavras; narrador edge Antonio +0% a 3,10 palavras/s; timeline v2 com segmentos e item_atual; CLI --fallback NOME/--ranking/--tema; v1 movida para legado/; 170 testes verdes; mais 20 rankings top5_* criados por outra sessão e mantidos a pedido do usuário)
- [x] R2 — Motor gráfico v2 (20/11/2026: `figure_renderer.py` 6 idades x 4 expressões, 8 cabelos, 6 roupas, 12 acessórios, piscar e boca; `layout_renderer.py` faixa vermelha, escada, etiquetas, rótulo amarelo; `output/contact_sheet_r2.png`; **aguarda aprovação visual**)
- [x] R3 — Narrador Chatterbox pt-BR (20/11/2026: `.venv-tts` Python 3.12, torch 2.6.0+cu124, chatterbox-tts 0.1.7 MIT, faster-whisper `small` para alinhar palavras; motor `chatterbox` via `tools/tts_worker.py`; **voz escolhida de ouvido: Chatterbox "calmo"** (exaggeration 0,4, cfg_weight 0,3, temperature 0,7), ~3,9 palavras/s; edge fica de reserva; amostras em `output/vozes/`)
- [x] Rodada 1 de rankings — `crises` (20/11/2026: `output/crises_v3.mp4`, 61,000 s, voz Chatterbox calmo, roteiro de 200 palavras ajustado pelo Gemini medindo o áudio real; melhorias: foco no item narrado com os outros esmaecidos, "?" pulsando no gancho, emojis com anel amarelo, emoji parado durante o zoom — corrigido o salto de lado)
- [x] Rodada 2 — `salario` (20/11/2026: `output/salario_v1.mp4`; novidade: barra de progresso em segmentos sob o título; aprovado)
- [x] Rodada 3 — `top5_animais_extintos` (20/11/2026: `output/animais_v1.mp4`; pedido do usuário: "mais energia, está morno". Novidades: efeitos sonoros procedurais `sfx.py` (whoosh, pop, impacto, subida antes do 1º, ding no CTA; `--sem-sfx` desliga), número do item batendo na tela, flash e tremida na entrada, faíscas nos emojis, alarme vermelho pulsando no 1º lugar, voz Chatterbox expressiva (exaggeration 0,75, cfg 0,35, temperature 0,8) e regras de retenção no prompt do Gemini (pontes entre itens, revelação por item, tensão crescente). Aguarda aprovação.)
- [x] Rodada 4 — `top5_comidas_caras` (20/11/2026: `output/comidas_v2.mp4` + `output/comidas_v2_creditos.txt`; aprendizados da rodada 3 aplicados: 1º quadro com close extremo no rosto do 1º lugar e título gigante (miniatura), fotos reais por item do Wikimedia Commons só com licença comercial (PD, CC0, CC BY, CC BY-SA) via `imagens.py` com créditos para a descrição, cartão de foto que aparece grande e vai para o canto, fechamento com desafio "comenta a palavra" (`palavra_chave`). Animais v1 recebeu ajustes do usuário, que viraram estes aprendizados.)
- [~] PIVÔ 2 — Minissérie emocional (21/11/2026, pedido do usuário: rankings com pouco engajamento; formato novela/vida real, com cenários). Piloto `output/minisserie/ingratidao_ep1.mp4` ("O Preço da Ingratidão", ep. 1): `tools/minisserie_ideias.py` (Gemini propõe séries), `tools/novela_roteiro.py` (Gemini escreve o episódio em `novela_schema.Episodio`), `novela_audio.py` (vozes Edge pt-BR por personagem — Chatterbox abandonado por sotaque com "R" puxado —, efeitos, chuva, trilha), `cenarios.py` (cenários flat), `novela_hf.py` (projeto HyperFrames em `motion/ingratidao_ep1`: close + título no quadro 0, câmera por fala com limites, boca nas palavras, expressões novas raiva/triste com lágrimas, chuva, carro, destaques, nomes, legendas, cartão CONTINUA), render pelo `tools/hf.py`. Aguarda avaliação do usuário.
- [ ] Próximos rankings (formato antigo, pausado), um por vez: `salario` e os 20 `top5_*`. Para cada um: `python tools/revisar_rankings.py NOME --pendentes --gravar` (ajusta à voz Chatterbox medindo o áudio real), depois `python main.py --fallback NOME`.
- [x] R4 — Montagem v2 (20/11/2026: `montagem.py`; `output/ranking_teste.mp4` 1080x1920, 30 fps, 61,000 s, 1830 quadros, h264_nvenc, render ~85 s; motion pedido pelo usuário: gancho abre no "?" do último item, câmera por item, punch-in no rosto a cada emoji, tremida curta, revelação progressiva das etiquetas, cartão CTA "curte/comenta/segue"; `output/contact_sheet_r4.png`)
- [x] R5 — Gemini de rankings (20/11/2026: `script_generator.py` com `gemini-3.8-flash` e reservas 3.5/2.5; prompt de roteirista viral com gancho, CTA antes do último item, visuais por palavra e regras de TTS; até 3 tentativas com feedback; reserva OpenAI-compatível; fallback local; `--tema` na CLI; `tools/revisar_rankings.py` revisou os rankings locais, backup em `output/rankings/backup_20261120/`)
- [ ] R6 — Robustez e novos layouts

Decisões tomadas: música de fundo sempre ligada (20/11; `--sem-bgm` desliga; `assets/bgm.mp3` tem prioridade sobre a trilha gerada); execução pelo Claude Code local; duração de 61,0 s; o PC tem GPU (marca e VRAM a confirmar na Fase 0).

### PIVÔ 3 — "Você é o Maquinista" (24/11/2026)
- Formato: 61 s, dilema do bonde (domínio público; nada do jogo/arte "Trial by Trolley"). Narradora Thalita (Edge, +22%,
  3,36 palavras/s), terceira pessoa imersiva; contagem regressiva de 10 s (51–61 s) com "A ou B?".
- Referência obrigatória: `docs/referencias/animated-shorts-kit` (fórmula de roteiro, gramática de câmera medida).
- Pipeline: `maquinista/epN.json` (roteiro escrito pelo Claude) → `tools/maquinista_voz.py` (voz + palavras) →
  `tools/maquinista_som.py` (mixagem com sons reais PD/CC0 do Commons + eventos) → `tools/maquinista_sprites.py`
  (personagens 2D) → `motion/trolley` (Remotion + three.js: mundo 3D, câmera contínua que pousa na palavra) →
  `node stills.mjs` (quadros de checagem) → `npx remotion render src/index.ts Video`.
- Desvios do kit, aceitos pelo usuário: pedido de comentário + 10 s de contagem no fim; legendas coloridas (em 1150 px,
  zona segura do TikTok, em vez de 70 % da altura); narrador fala com "você".
- Ep. 2 (25/11/2026, `output/maquinista/ep2_final.mp4`): camada de thriller pedida pelo usuário depois do ep. 1.
  Gancho in media res (trilho + faíscas + rangido antes da voz), tremor de câmera, ângulo holandês no pânico, inserts de
  0,8 s com distância até o desvio, montagem acelerada na contagem, congelamento final com apito → silêncio, 1 s de
  silêncio absoluto na virada, riser, tec-tec do trilho acelerando, narradora urgente (+32%, compressão, respiradas).
  Vários cortes secos contrariam o kit (~1 por vídeo): escolha do usuário; ficam marcados com `tag` no `plano.json`.
  Episódio ativo = imports `./ep2/` em `dados.ts`, `camera.ts`, `camadas.tsx`, `Video.tsx`; o código do ep. 1 está em
  `motion/trolley/arquivo/ep1_src`.
- Ep. 3 (25/11/2026, `output/maquinista/ep3_maquinista.mp4`): "A última vacina" (vacina contra zumbi x a cientista
  que sabe fazer outra; virada: a mordida no seu braço). Gancho novo (regra do formato daqui em diante): pergunta
  gigante "QUEM VOCÊ SALVA?" desde o quadro 0 + voz desde o quadro 0, 1ª imagem = quem está no trilho chorando.
  **Banco de takes**: `node takes.mjs ep2 nome:f0-f1,...` renderiza trechos LIMPOS (só o mundo 3D) do episódio ativo em
  `motion/trolley/public/takes/` (+ `takes.json`). No `plano.json`, chave com `"take"` mostra o clipe no lugar do 3D;
  a 1ª chave da janela traz `"alinha"` (fala idêntica nos dois episódios) ou `"de"` (tempo no episódio de origem).
  O roteiro que repete falas usa `"atempo"` igual ao do episódio de origem. O ep. 3 reaproveita do ep. 2: trilho +
  rosto, freio quebrando, 3 inserts, alavanca do desvio e 7 dos 11 cortes da contagem + congelamento final.
  Banco de ideias de dilemas: `maquinista/ideias.md`.
