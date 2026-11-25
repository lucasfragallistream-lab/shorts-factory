"""Pydantic models for ranking videos: Ranking -> Item -> Personagem.

A ranking is narrated by a single voice in segments: the opening, one segment per item
(in order) and the closing. Each item shows one generic, parametric character.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

import config

Layout = Literal["escada", "podio", "fila"]
Idade = Literal["crianca", "adolescente", "jovem", "adulto", "meia_idade", "idoso"]
Sexo = Literal["masculino", "feminino"]
Pele = Literal["clara", "media", "morena", "negra"]
Cabelo = Literal["curto", "espetado", "liso", "cacheado", "comprido", "coque", "rabo", "careca"]
CorCabelo = Literal["preto", "castanho", "loiro", "ruivo", "grisalho", "branco"]
Roupa = Literal["camiseta", "moletom", "camisa", "social", "vestido", "jaqueta"]
Cor = Literal["azul", "azul_claro", "vermelho", "verde", "amarelo", "roxo", "laranja", "rosa", "cinza", "preto",
              "branco", "bege"]
Acessorio = Literal["oculos", "barba", "bigode", "caneca", "mochila", "fone", "gravata", "celular", "bone",
                    "bengala", "sacola", "colar"]
Expressao = Literal["feliz", "preocupado", "cansado", "chocado", "raiva", "triste"]

_PALAVRA = re.compile(r"[\wÀ-ÿ]+(?:[-'][\wÀ-ÿ]+)*", re.UNICODE)


def contar_palavras(texto: str) -> int:
    return len(_PALAVRA.findall(texto))


def _limpar(v: str) -> str:
    v = " ".join(v.split())
    if contar_palavras(v) == 0:
        raise ValueError("texto sem palavras")
    return v


class Personagem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idade: Idade = "adulto"
    sexo: Sexo = "masculino"
    pele: Pele = "media"
    cabelo: Cabelo = "curto"
    cor_cabelo: CorCabelo = "preto"
    roupa: Roupa = "camiseta"
    cor_roupa: Cor = "azul"
    acessorios: list[Acessorio] = Field(default_factory=list, max_length=config.ACESSORIOS_MAX)
    expressao: Expressao = "feliz"

    @field_validator("acessorios")
    @classmethod
    def _sem_repetir(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("acessório repetido")
        return v


class Visual(BaseModel):
    """An emoji that pops on screen when `palavra` is spoken in its segment."""
    model_config = ConfigDict(extra="forbid")

    palavra: str = Field(min_length=1, max_length=30)  # word (or word prefix) of the narration that triggers it
    emoji: str = Field(min_length=1, max_length=12)

    @field_validator("emoji")
    @classmethod
    def _emoji(cls, v: str) -> str:
        v = v.strip()
        if not v or v.isascii():
            raise ValueError("emoji precisa ser um caractere emoji")
        return v

    @field_validator("palavra")
    @classmethod
    def _palavra(cls, v: str) -> str:
        return v.strip().split()[0]


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rotulo: str = Field(min_length=1, max_length=24)  # etiqueta sobre o personagem, ex.: "13 anos"
    narracao: str = Field(min_length=1, max_length=400)
    personagem: Personagem = Field(default_factory=Personagem)
    visuais: list[Visual] = Field(default_factory=list, max_length=config.VISUAIS_MAX)
    # search term (English works best) for a real photo of this item on Wikimedia Commons
    imagem: str | None = Field(default=None, max_length=80)

    @field_validator("narracao")
    @classmethod
    def _narracao(cls, v: str) -> str:
        return _limpar(v)

    @field_validator("rotulo")
    @classmethod
    def _rotulo(cls, v: str) -> str:
        return " ".join(v.split())


class Segmento(BaseModel):
    """One narrated piece: opening, an item, or closing."""

    tipo: Literal["abertura", "item", "cta", "fechamento"]
    item: int | None  # index into Ranking.itens for tipo == "item"
    rotulo: str | None
    texto: str
    visuais: list[Visual] = Field(default_factory=list)


class Ranking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1, max_length=60)  # faixa vermelha do topo
    layout: Layout = "escada"
    abertura: str = Field(min_length=1, max_length=300)
    itens: list[Item] = Field(min_length=config.ITENS_MIN, max_length=config.ITENS_MAX)
    fechamento: str = Field(min_length=1, max_length=300)
    # call to action narrated right before the last item (follow, like, comment if you agree)
    cta: str | None = Field(default=None, max_length=200)
    # one word viewers comment to prove they watched to the end (shown big during the closing)
    palavra_chave: str | None = Field(default=None, max_length=20)
    visuais_abertura: list[Visual] = Field(default_factory=list, max_length=config.VISUAIS_MAX)
    visuais_fechamento: list[Visual] = Field(default_factory=list, max_length=config.VISUAIS_MAX)

    @field_validator("abertura", "fechamento")
    @classmethod
    def _textos(cls, v: str) -> str:
        return _limpar(v)

    @field_validator("palavra_chave")
    @classmethod
    def _palavra_chave(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not re.fullmatch(r"[\wÀ-ÿ-]+", v):
            raise ValueError("palavra_chave precisa ser uma única palavra")
        return v

    @field_validator("cta")
    @classmethod
    def _cta(cls, v: str | None) -> str | None:
        return _limpar(v) if v else None

    @field_validator("titulo")
    @classmethod
    def _titulo(cls, v: str) -> str:
        return " ".join(v.split())

    def segmentos(self) -> list[Segmento]:
        out = [Segmento(tipo="abertura", item=None, rotulo=None, texto=self.abertura, visuais=self.visuais_abertura)]
        itens = [Segmento(tipo="item", item=i, rotulo=it.rotulo, texto=it.narracao, visuais=it.visuais)
                 for i, it in enumerate(self.itens)]
        out += itens[:-1]
        if self.cta:
            out.append(Segmento(tipo="cta", item=None, rotulo=None, texto=self.cta))
        out.append(itens[-1])
        out.append(Segmento(tipo="fechamento", item=None, rotulo=None, texto=self.fechamento,
                            visuais=self.visuais_fechamento))
        return out

    @property
    def palavras(self) -> int:
        return sum(contar_palavras(s.texto) for s in self.segmentos())

    def duracao_fala_estimada(self) -> float:
        """Estimated narration time in seconds (no pauses)."""
        return self.palavras / config.NARRADOR["palavras_por_segundo"]

    @classmethod
    def carregar(cls, caminho: str | Path) -> "Ranking":
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        return cls.model_validate(dados)


def listar_fallbacks() -> list[str]:
    return sorted(p.stem for p in config.RANKINGS.glob("*.json"))
