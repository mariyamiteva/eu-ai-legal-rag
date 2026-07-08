from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .answering import answer_question
from .store import search


app = FastAPI(title="EU AI Legal RAG", version="0.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=5)
    top_k: int = Field(default=8, ge=1, le=30)
    categories: list[str] | None = None
    tags: list[str] | None = None
    source_ids: list[str] | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = Field(default=8, ge=1, le=50)
    categories: list[str] | None = None
    tags: list[str] | None = None
    source_ids: list[str] | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search")
def search_endpoint(payload: SearchRequest) -> dict:
    evidence = search(
        payload.query,
        top_k=payload.top_k,
        categories=payload.categories,
        tags=payload.tags,
        source_ids=payload.source_ids,
    )
    return {"evidence": [ev.__dict__ for ev in evidence]}


@app.post("/ask")
def ask_endpoint(payload: AskRequest) -> dict:
    evidence = search(
        payload.question,
        top_k=payload.top_k,
        categories=payload.categories,
        tags=payload.tags,
        source_ids=payload.source_ids,
    )
    return answer_question(payload.question, evidence)
