import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


@pytest.fixture(scope="session")
def timeline_mock(tmp_path_factory):
    """Full 61 s mock-voice timeline for the 'crises' fallback ranking (offline)."""
    import config
    import voice_engine as ve
    from schemas import Ranking

    pasta = tmp_path_factory.mktemp("tl")
    r = Ranking.carregar(config.RANKINGS / "crises.json")
    res = ve.gerar_audio(r, ve.MotorMock(), 61.0, pasta / "voz.wav", pasta / "timeline.json")
    return res.timeline, json.loads(res.timeline.read_text(encoding="utf-8"))
