from __future__ import annotations

import argparse
import json
from pathlib import Path

from .answering import answer_question
from .discover import discover_related_links, save_discovered
from .ingest import ingest_sources
from .sources import load_sources
from .store import search


def main() -> None:
    parser = argparse.ArgumentParser(prog="eu_legal_rag")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Fetch, chunk, embed and store source documents")
    ingest_p.add_argument("--sources", default="data/sources.eu_ai_legal.yaml")
    ingest_p.add_argument("--recreate", action="store_true", help="Recreate Qdrant collection before inserting")
    ingest_p.add_argument("--category", action="append", help="Only ingest sources in this category; can be repeated")
    ingest_p.add_argument("--tag", action="append", help="Only ingest sources with this tag; can be repeated")

    ask_p = sub.add_parser("ask", help="Retrieve evidence and optionally generate an answer")
    ask_p.add_argument("question")
    ask_p.add_argument("--top-k", type=int, default=8)
    ask_p.add_argument("--category", action="append")
    ask_p.add_argument("--tag", action="append")
    ask_p.add_argument("--source-id", action="append")

    search_p = sub.add_parser("search", help="Retrieve evidence only")
    search_p.add_argument("query")
    search_p.add_argument("--top-k", type=int, default=8)
    search_p.add_argument("--category", action="append")
    search_p.add_argument("--tag", action="append")

    discover_p = sub.add_parser("discover", help="Discover official related links from seed pages")
    discover_p.add_argument("--sources", default="data/sources.eu_ai_legal.yaml")
    discover_p.add_argument("--out", default="data/discovered.official_links.json")
    discover_p.add_argument("--max-depth", type=int, default=1)

    args = parser.parse_args()

    if args.command == "ingest":
        sources = load_sources(args.sources)
        sources = filter_sources(sources, categories=args.category, tags=args.tag)
        stats = ingest_sources(sources, recreate_collection=args.recreate)
        print(json.dumps(stats, indent=2))

    elif args.command == "ask":
        evidence = search(
            args.question,
            top_k=args.top_k,
            categories=args.category,
            tags=args.tag,
            source_ids=args.source_id,
        )
        result = answer_question(args.question, evidence)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "search":
        evidence = search(args.query, top_k=args.top_k, categories=args.category, tags=args.tag)
        print(json.dumps([ev.__dict__ for ev in evidence], indent=2, ensure_ascii=False))

    elif args.command == "discover":
        sources = load_sources(args.sources)
        results = discover_related_links(sources, max_depth=args.max_depth)
        save_discovered(results, args.out)
        print(f"Wrote {len(results)} discovered links to {Path(args.out).resolve()}")


def filter_sources(sources, categories: list[str] | None, tags: list[str] | None):
    result = []
    for source in sources:
        if categories and source.category not in categories:
            continue
        if tags and not set(tags).intersection(source.tags):
            continue
        result.append(source)
    return result


if __name__ == "__main__":
    main()
