from __future__ import annotations

from collections.abc import Iterable

from .chunking import chunk_document
from .fetch import fetch_many
from .schemas import Source
from .store import ensure_collection, upsert_chunks


def ingest_sources(sources: Iterable[Source], recreate_collection: bool = False) -> dict:
    sources_list = list(sources)
    ensure_collection(recreate=recreate_collection)
    raw_documents = fetch_many(sources_list)

    all_chunks = []
    for document in raw_documents:
        chunks = chunk_document(document)
        print(f"{document.source.id}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    inserted = upsert_chunks(all_chunks)
    return {
        "sources_requested": len(sources_list),
        "sources_fetched": len(raw_documents),
        "chunks_inserted": inserted,
    }
