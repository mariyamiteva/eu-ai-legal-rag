from __future__ import annotations

import hashlib
import re

from .schemas import Chunk, RawDocument
from .settings import get_settings


HEADING_RE = re.compile(
    r"(?im)^(article\s+\d+[a-z]?|annex\s+[ivxlcdm]+|chapter\s+[ivxlcdm]+|section\s+\d+|recital\s*\(?\d+\)?|\(\d+\))\b"
)


def chunk_document(document: RawDocument) -> list[Chunk]:
    settings = get_settings()
    sections = split_into_legal_sections(document.text)
    chunks: list[Chunk] = []
    ordinal = 0

    for section in sections:
        for piece in split_with_overlap(section, settings.chunk_size_chars, settings.chunk_overlap_chars):
            piece = piece.strip()
            if len(piece) < 250:
                continue
            chunk_id = make_chunk_id(document.source.id, ordinal, piece)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    source_id=document.source.id,
                    source_title=document.source.title,
                    source_url=document.source.url,
                    category=document.source.category,
                    text=piece,
                    ordinal=ordinal,
                    tags=document.source.tags,
                    celex=document.source.celex,
                    extra={"content_type": document.content_type, "fetched_url": document.fetched_url},
                )
            )
            ordinal += 1
    return chunks


def split_into_legal_sections(text: str) -> list[str]:
    matches = list(HEADING_RE.finditer(text))
    if len(matches) < 4:
        return [text]

    sections: list[str] = []
    starts = [m.start() for m in matches] + [len(text)]
    if starts[0] > 0:
        prefix = text[: starts[0]].strip()
        if prefix:
            sections.append(prefix)

    for i in range(len(starts) - 1):
        section = text[starts[i] : starts[i + 1]].strip()
        if section:
            sections.append(section)
    return sections


def split_with_overlap(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        window = text[start:end]
        if end < len(text):
            break_at = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("; "))
            if break_at > size * 0.55:
                end = start + break_at + 1
                window = text[start:end]
        chunks.append(window)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def make_chunk_id(source_id: str, ordinal: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{source_id}:{ordinal:05d}:{digest}"
