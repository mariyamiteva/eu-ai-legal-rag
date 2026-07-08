from __future__ import annotations

from typing import Iterable

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from .embeddings import embed_texts, embedding_dimension
from .schemas import Chunk, Evidence
from .settings import get_settings


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(recreate: bool = False) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]
    if recreate and settings.qdrant_collection in collections:
        client.delete_collection(settings.qdrant_collection)
        collections.remove(settings.qdrant_collection)

    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=embedding_dimension(), distance=Distance.COSINE),
        )
        client.create_payload_index(settings.qdrant_collection, field_name="source_id", field_schema="keyword")
        client.create_payload_index(settings.qdrant_collection, field_name="category", field_schema="keyword")
        client.create_payload_index(settings.qdrant_collection, field_name="tags", field_schema="keyword")


def upsert_chunks(chunks: Iterable[Chunk], batch_size: int = 64) -> int:
    settings = get_settings()
    client = get_qdrant_client()
    ensure_collection(recreate=False)

    total = 0
    batch: list[Chunk] = []
    for chunk in chunks:
        batch.append(chunk)
        if len(batch) >= batch_size:
            total += _upsert_batch(client, settings.qdrant_collection, batch)
            batch.clear()
    if batch:
        total += _upsert_batch(client, settings.qdrant_collection, batch)
    return total


def _upsert_batch(client: QdrantClient, collection: str, batch: list[Chunk]) -> int:
    vectors = embed_texts([c.text for c in batch])
    points = []
    for chunk, vector in zip(batch, vectors, strict=True):
        points.append(
            PointStruct(
                id=stable_point_id(chunk.id),
                vector=vector.tolist(),
                payload={
                    "chunk_id": chunk.id,
                    "source_id": chunk.source_id,
                    "source_title": chunk.source_title,
                    "source_url": chunk.source_url,
                    "category": chunk.category,
                    "text": chunk.text,
                    "ordinal": chunk.ordinal,
                    "tags": chunk.tags,
                    "celex": chunk.celex,
                    **chunk.extra,
                },
            )
        )
    client.upsert(collection_name=collection, points=points, wait=True)
    return len(points)


def stable_point_id(chunk_id: str) -> int:
    # Qdrant accepts UUID or unsigned integer IDs. Keep deterministic integer IDs.
    import hashlib

    return int(hashlib.sha256(chunk_id.encode("utf-8")).hexdigest()[:15], 16)


def search(
    query: str,
    top_k: int = 8,
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    source_ids: list[str] | None = None,
) -> list[Evidence]:
    settings = get_settings()
    client = get_qdrant_client()
    query_vector = embed_texts([query])[0].tolist()
    qfilter = build_filter(categories=categories, tags=tags, source_ids=source_ids)

    hits = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=qfilter,
        limit=top_k,
        with_payload=True,
    )
    return [
        Evidence(
            chunk_id=hit.payload.get("chunk_id", ""),
            source_id=hit.payload.get("source_id", ""),
            source_title=hit.payload.get("source_title", ""),
            source_url=hit.payload.get("source_url", ""),
            category=hit.payload.get("category", ""),
            text=hit.payload.get("text", ""),
            score=float(hit.score),
            tags=list(hit.payload.get("tags", [])),
        )
        for hit in hits
    ]


def build_filter(
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    source_ids: list[str] | None = None,
) -> Filter | None:
    must = []
    if categories:
        must.append(FieldCondition(key="category", match=MatchAny(any=categories)))
    if tags:
        must.append(FieldCondition(key="tags", match=MatchAny(any=tags)))
    if source_ids:
        must.append(FieldCondition(key="source_id", match=MatchAny(any=source_ids)))
    if not must:
        return None
    return Filter(must=must)
