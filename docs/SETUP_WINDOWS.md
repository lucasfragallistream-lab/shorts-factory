# Setup do Windows (parte manual da Fase 0)

Tempo estimado: 15 minutos. Use o PowerShell normal. Se o winget pedir permissão de administrador, aceite.

## 1. Instalar as ferramentas

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg -e
winget install --id rtk-ai.rtk -e
irm https://claude.ai/install.ps1 | iex
```

Feche o PowerShell e abra outro, para o PATH atualizar.

## 2. Conferir

```powershell
git --version
python --version
ffmpeg -version
rtk gain
claude --version
```

- `rtk gain` precisa mostrar o painel de economia. Se aparecer erro, foi instalado outro programa com o mesmo nome.
- Se `python` abrir a Microsoft Store, tudo bem: o Claude Code resolve isso na Fase 0 usando `py -3.12`.

## 3. Variáveis de ambiente (uma vez só)

```powershell
setx CLAUDE_CODE_USE_POWERSHELL_TOOL 0
setx DO_NOT_TRACK 1
setx PYTHONUTF8 1
```

- A primeira faz o Claude Code rodar tudo pelo Git Bash, onde o rtk consegue comprimir a saída dos comandos.
- A segunda desliga as estatísticas de uso do caveman.
- Se a `GEMINI_API_KEY` ainda não estiver configurada: `setx GEMINI_API_KEY "sua-chave"`.

Feche o PowerShell e abra outro.

## 4. Primeiro login no Claude Code e hook do rtk

```powershell
claude
```

Faça o login e saia com `/exit`. Depois:

```powershell
rtk init -g
```

Responda `y` quando ele perguntar se pode alterar o `settings.json`.

## 5. Abrir o projeto e instalar o caveman

```powershell
cd C:\fabricadevideo\shorts-factory
claude
```

Dentro do Claude Code:

```
/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman
```

Saia com `/exit` e abra `claude` de novo para carregar o plugin.

## 6. Começar

Dentro do Claude Code, digite `/caveman` e cole o prompt da Fase 0 de `docs\PROMPTS.md`.
