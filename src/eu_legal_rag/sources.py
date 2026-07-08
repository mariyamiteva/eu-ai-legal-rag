from __future__ import annotations

from pathlib import Path
import yaml

from .schemas import Source


def load_sources(path: str | Path) -> list[Source]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    if not sources:
        raise ValueError(f"No sources found in {path}")

    result: list[Source] = []
    seen: set[str] = set()
    for item in sources:
        source = Source(
            id=item["id"],
            title=item["title"],
            url=item["url"],
            celex=item.get("celex"),
            category=item.get("category", "unknown"),
            priority=int(item.get("priority", 50)),
            language=item.get("language", "en"),
            tags=list(item.get("tags", [])),
        )
        if source.id in seen:
            raise ValueError(f"Duplicate source id: {source.id}")
        seen.add(source.id)
        result.append(source)
    return result
