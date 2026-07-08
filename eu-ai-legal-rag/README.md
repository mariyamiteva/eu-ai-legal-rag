# EU AI Legal RAG

Reference architecture for a legal/document reasoning system over the EU AI Act, GDPR, official guidance, standards pages, and EU legislation that is directly or commonly connected to AI Act compliance.

The project is designed as an extensible RAG pipeline:

1. source registry in `data/sources.eu_ai_legal.yaml`
2. optional discovery of related official links from seed pages
3. ingestion of HTML/PDF documents
4. chunking with legal metadata
5. embeddings into Qdrant
6. retrieval with citations
7. optional answer generation through a configurable LLM
8. FastAPI endpoint for applications

This is not legal advice. The system is meant to support research, gap analysis, and drafting workflows. Human legal review is still required.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

docker compose up -d qdrant
python -m eu_legal_rag.cli ingest --sources data/sources.eu_ai_legal.yaml
python -m eu_legal_rag.cli ask "What obligations apply to high-risk AI systems under the AI Act and how does GDPR interact?"
uvicorn eu_legal_rag.api:app --reload
```

Then call:

```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Compare AI Act Article 5 prohibited practices with GDPR automated decision-making obligations.","top_k":8}'
```

## Updating the document set

Official EU guidance and implementing materials evolve. Run discovery periodically to add newly linked official documents:

```bash
python -m eu_legal_rag.cli discover \
  --sources data/sources.eu_ai_legal.yaml \
  --out data/discovered.official_links.json \
  --max-depth 1
```

Review the discovered links before ingestion. For production, keep a reviewed allowlist rather than ingesting every discovered URL automatically.

## Design choices

- Qdrant is used because it can run locally and supports payload filters.
- SentenceTransformers is the default embedding backend to avoid vendor lock-in.
- LLM generation is optional. Without `OPENAI_API_KEY`, the system returns retrieved evidence only.
- Source metadata is preserved so answers can cite document title, URL, chunk id, and legal category.
- The source registry includes primary law, AI Act-amended legislation, GDPR/privacy materials, Commission guidance, AI Office/GPAI materials, standards pages, and adjacent EU digital/product/cyber legislation.
