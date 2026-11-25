"""Project-wide constants: video format, paths, narrator voice, ranking vocabulary and timing targets."""
from __future__ import annotations

from pathlib import Path

# --- Paths -----------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent
ASSETS = RAIZ / "assets"
FONTES = ASSETS / "fonts"
RANKINGS = ASSETS / "rankings"
VOZES = ASSETS / "vozes"
BGM = ASSETS / "bgm.mp3"
CACHE = RAIZ / "cache"
OUTPUT = RAIZ / "output"
LOGS = RAIZ / "logs"
ULTIMO_ERRO = LOGS / "ultimo_erro.txt"
FFMPEG_LOG = LOGS / "ffmpeg.log"

# --- Video format ----------------------------------------------------------
LARGURA = 1080
ALTURA = 1920
FPS = 30
SUPERSAMPLING = 2

# --- Duration (plan, section 6, item 1) ------------------------------------
DURACAO_ALVO = 61.0  # seconds -> 1830 frames
DURACAO_MINIMA = 60.0  # the video never ships shorter than this
FALA_ALVO_MIN = 56.0  # target window for pure narration time
FALA_ALVO_MAX = 59.0
PAUSA_ENTRE_SEGMENTOS = 0.35  # s between opening / items / closing (grows or shrinks to hit 61.0 s)
TOLERANCIA_ESTIMATIVA = 2.5  # s; the words/s estimate ignores punctuation pauses (real fit is checked on audio)

# --- Ranking vocabulary (schemas.py) ---------------------------------------
LAYOUTS = ("escada", "podio", "fila")
ITENS_MIN, ITENS_MAX = 3, 5
IDADES = ("crianca", "adolescente", "jovem", "adulto", "meia_idade", "idoso")
SEXOS = ("masculino", "feminino")
PELES = ("clara", "media", "morena", "negra")
CABELOS = ("curto", "espetado", "liso", "cacheado", "comprido", "coque", "rabo", "careca")
CORES_CABELO = ("preto", "castanho", "loiro", "ruivo", "grisalho", "branco")
ROUPAS = ("camiseta", "moletom", "camisa", "social", "vestido", "jaqueta")
CORES = ("azul", "azul_claro", "vermelho", "verde", "amarelo", "roxo", "laranja", "rosa", "cinza", "preto", "branco",
         "bege")
ACESSORIOS = ("oculos", "barba", "bigode", "caneca", "mochila", "fone", "gravata", "celular", "bone", "bengala",
              "sacola", "colar")
ACESSORIOS_MAX = 3
EXPRESSOES = ("feliz", "preocupado", "cansado", "chocado", "raiva", "triste")
VISUAIS_MAX = 4  # emojis that pop per narrated segment

# --- Narrator --------------------------------------------------------------
# One narrator for the whole video. Phase R3 makes Chatterbox (pt-BR, MIT) the main engine;
# edge-tts stays as backup. palavras_por_segundo: measured with tools/medir_vozes.py.
NARRADOR: dict = {
    "voz": "pt-BR-AntonioNeural",
    "rate": "+0%",
    "pitch": "+0Hz",
    "palavras_por_segundo": 3.90,  # Chatterbox "calmo" (tools/comparar_vozes.py, 20/11/2026); edge was 3.10
}

# --- CLI defaults ----------------------------------------------------------
TTS_MOTORES = ("edge", "mock", "chatterbox")
# Chatterbox Multilingual (R3). Optional reference voice to clone: assets/vozes/narrador.wav (5-10 s,
# a recording you have the rights to). Without it the model's default voice is used.
# 20/11/2026: "calmo" (0.4/0.3/0.7) sounded flat ("morno"); user asked for more energy -> expressive
CHATTERBOX = {"exaggeration": 0.75, "cfg_weight": 0.35, "temperature": 0.8}
WHISPER_MODELO = "small"  # faster-whisper model for word alignment

# --- Script writer (R5) ----------------------------------------------------
# Override with the GEMINI_MODEL env var. Fallbacks are tried in order if the main model fails.
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_MODELOS_RESERVA = ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
RANKINGS_GERADOS = OUTPUT / "rankings"
TTS_PADRAO = "chatterbox"  # chosen 20/11/2026; edge stays as backup
ESTILO_BGM = "leve"
