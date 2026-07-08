from __future__ import annotations

import os
from textwrap import dedent

from openai import OpenAI

from .schemas import Evidence
from .settings import get_settings


SYSTEM_PROMPT = """
You are a legal-research assistant for EU AI regulation.
Use only the supplied evidence. Do not invent legal obligations.
Always separate: binding law, official guidance, draft guidance, standards, and your own synthesis.
If evidence is insufficient, say what is missing.
Return citations in the form [S1], [S2], etc.
This is not legal advice.
""".strip()


def build_context(evidence: list[Evidence]) -> str:
    blocks = []
    for idx, ev in enumerate(evidence, start=1):
        blocks.append(
            dedent(
                f"""
                [S{idx}]
                title: {ev.source_title}
                url: {ev.source_url}
                category: {ev.category}
                score: {ev.score:.4f}
                chunk_id: {ev.chunk_id}
                text:
                {ev.text}
                """
            ).strip()
        )
    return "\n\n---\n\n".join(blocks)


def answer_question(question: str, evidence: list[Evidence]) -> dict:
    settings = get_settings()
    context = build_context(evidence)
    citations = [
        {
            "label": f"S{idx}",
            "source_id": ev.source_id,
            "title": ev.source_title,
            "url": ev.source_url,
            "chunk_id": ev.chunk_id,
            "score": ev.score,
            "category": ev.category,
        }
        for idx, ev in enumerate(evidence, start=1)
    ]

    if not settings.openai_api_key or not settings.llm_model:
        return {
            "answer": "LLM generation is disabled. Set OPENAI_API_KEY and LLM_MODEL to generate a synthesized answer. Retrieved evidence is returned below.",
            "citations": citations,
            "evidence_text": context,
        }

    client = OpenAI(api_key=settings.openai_api_key or os.environ.get("OPENAI_API_KEY"))
    user_prompt = f"""
Question:
{question}

Evidence:
{context}

Draft a concise but complete answer. Include citation labels next to each legal claim.
""".strip()

    response = client.responses.create(
        model=settings.llm_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return {"answer": response.output_text, "citations": citations}
