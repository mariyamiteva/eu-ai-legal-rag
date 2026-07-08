from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    category: str
    priority: int = 50
    language: str = "en"
    celex: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RawDocument:
    source: Source
    text: str
    content_type: str
    fetched_url: str


@dataclass(frozen=True)
class Chunk:
    id: str
    source_id: str
    source_title: str
    source_url: str
    category: str
    text: str
    ordinal: int
    tags: list[str]
    celex: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    chunk_id: str
    source_id: str
    source_title: str
    source_url: str
    category: str
    text: str
    score: float
    tags: list[str]
