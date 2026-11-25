"""Miniseries episode format (vertical novela / real-life drama), written by Gemini, rendered by novela_hf.py.

An episode is a list of scenes (one setting each); a scene is a list of lines. Every line is spoken by the
narrator or by a cast member with an emotion and a framing (close on the speaker's face, medium shot or wide
shot). The first frame shows `titulo` huge over a close-up of the protagonist's face.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from schemas import Personagem, contar_palavras

Cenario = Literal["calcada_casa", "porta_casa", "sala", "cozinha", "quarto", "carro_luxo"]
CENARIOS = ("calcada_casa", "porta_casa", "sala", "cozinha", "quarto", "carro_luxo")
Emocao = Literal["neutra", "triste", "chorando", "raiva", "deboche", "choque", "medo", "esperanca"]
Enquadramento = Literal["close", "medio", "geral"]
Objeto = Literal["malas", "carro_luxo"]
Papel = Literal["protagonista", "vilao", "vila", "aliado", "misterio"]
Gesto = Literal["aponta", "estende", "bracos_cima", "maos_rosto", "maos_cintura", "mao_peito"]
Acao = Literal["aproxima", "empurra", "abraca", "entra", "sai"]


class Membro(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,19}$")
    nome: str = Field(min_length=1, max_length=24)
    papel: Papel
    personagem: Personagem


class Fala(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quem: str  # "narrador" or a cast id
    texto: str = Field(min_length=1, max_length=220)
    emocao: Emocao = "neutra"
    enquadramento: Enquadramento = "medio"
    destaque: str | None = Field(default=None, max_length=28)  # big on-screen word/phrase for this line (optional)
    gesto: Gesto | None = None  # speaker's arm gesture; None = chosen from the emotion
    acao: Acao | None = None  # movement during the line (walk to, push, hug, enter, leave)
    alvo: str | None = None  # cast id the gesture/action is aimed at

    @field_validator("texto")
    @classmethod
    def _texto(cls, v: str) -> str:
        return " ".join(v.split())


class Cena(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cenario: Cenario
    chuva: bool = False
    presentes: list[str] = Field(min_length=1, max_length=4)  # cast ids on screen, left to right
    objetos: list[Objeto] = Field(default_factory=list, max_length=3)  # props: malas on the ground, car arriving
    falas: list[Fala] = Field(min_length=1, max_length=10)


class MomentoChave(BaseModel):
    """The one moment per episode animated by Higgsfield (image-to-video from our own flat frame)."""
    model_config = ConfigDict(extra="forbid")

    cena: int = Field(ge=0)
    fala: int = Field(ge=0)
    prompt: str = Field(min_length=10, max_length=400)  # English motion prompt for the video model


class Episodio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serie: str = Field(max_length=60)
    numero: int = Field(ge=1, le=99)
    titulo: str = Field(min_length=1, max_length=60)  # frame 0, huge, over the protagonist's face
    elenco: list[Membro] = Field(min_length=1, max_length=5)
    cenas: list[Cena] = Field(min_length=1, max_length=5)
    pergunta: str = Field(min_length=1, max_length=120)  # on screen at the end (comment bait)
    proximo: str = Field(default="PARTE 2", max_length=30)
    momento_chave: MomentoChave | None = None

    @model_validator(mode="after")
    def _ids(self) -> "Episodio":
        ids = {m.id for m in self.elenco}
        if len(ids) != len(self.elenco):
            raise ValueError("ids repetidos no elenco")
        for c in self.cenas:
            for p in c.presentes:
                if p not in ids:
                    raise ValueError(f"cena com personagem desconhecido: {p}")
            for f in c.falas:
                if f.quem != "narrador" and f.quem not in ids:
                    raise ValueError(f"fala de personagem desconhecido: {f.quem}")
                if f.quem != "narrador" and f.quem not in c.presentes:
                    raise ValueError(f"{f.quem} fala mas não está presente na cena")
                if f.alvo is not None and (f.alvo not in c.presentes or f.alvo == f.quem):
                    raise ValueError(f"alvo inválido na fala de {f.quem}: {f.alvo}")
                if f.acao in ("aproxima", "empurra", "abraca") and (f.alvo is None or f.quem == "narrador"):
                    raise ValueError(f"ação {f.acao} precisa de quem (personagem) e alvo")
                if f.acao in ("entra", "sai") and f.quem == "narrador":
                    raise ValueError("o narrador não entra nem sai de cena")
        mk = self.momento_chave
        if mk is not None and (mk.cena >= len(self.cenas) or mk.fala >= len(self.cenas[mk.cena].falas)):
            raise ValueError("momento_chave aponta para cena/fala inexistente")
        return self

    @property
    def palavras(self) -> int:
        return sum(contar_palavras(f.texto) for c in self.cenas for f in c.falas)

    def membro(self, id_: str) -> Membro:
        return next(m for m in self.elenco if m.id == id_)

    def protagonista(self) -> Membro:
        return next((m for m in self.elenco if m.papel == "protagonista"), self.elenco[0])

    @classmethod
    def carregar(cls, caminho: str | Path) -> "Episodio":
        return cls.model_validate(json.loads(Path(caminho).read_text(encoding="utf-8")))
