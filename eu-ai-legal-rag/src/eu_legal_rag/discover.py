from __future__ import annotations

from collections import deque
from dataclasses import asdict
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from bs4 import BeautifulSoup
import httpx

from .schemas import Source
from .settings import get_settings


ALLOWED_DOMAINS = {
    "eur-lex.europa.eu",
    "digital-strategy.ec.europa.eu",
    "ai-act-service-desk.ec.europa.eu",
    "www.edpb.europa.eu",
    "edpb.europa.eu",
    "ec.europa.eu",
    "www.cencenelec.eu",
}

KEYWORDS = {
    "ai act",
    "artificial intelligence",
    "regulation (eu) 2024/1689",
    "gdpr",
    "data protection",
    "high-risk",
    "general-purpose ai",
    "gpai",
    "standardisation",
    "conformity assessment",
    "prohibited artificial intelligence practices",
}


def discover_related_links(seeds: list[Source], max_depth: int = 1) -> list[dict]:
    settings = get_settings()
    headers = {"User-Agent": settings.user_agent}
    queue = deque([(seed.url, 0, seed.id) for seed in seeds])
    seen: set[str] = set()
    results: list[dict] = []

    with httpx.Client(follow_redirects=True, timeout=settings.request_timeout_seconds, headers=headers) as client:
        while queue:
            url, depth, seed_id = queue.popleft()
            canonical = canonicalize(url)
            if canonical in seen:
                continue
            seen.add(canonical)
            if not is_allowed(canonical):
                continue
            try:
                response = client.get(canonical)
                response.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                results.append({"url": canonical, "seed_id": seed_id, "depth": depth, "error": str(exc)})
                continue

            content_type = response.headers.get("content-type", "").lower()
            title = canonical
            text_for_relevance = ""
            links: list[str] = []

            if "text/html" in content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.title.get_text(" ", strip=True) if soup.title else canonical
                text_for_relevance = soup.get_text(" ", strip=True)[:5000].lower()
                for a in soup.find_all("a", href=True):
                    links.append(canonicalize(urljoin(str(response.url), a["href"])))
            elif "pdf" in content_type or canonical.lower().endswith(".pdf"):
                title = canonical.rsplit("/", 1)[-1]
                text_for_relevance = title.lower()

            relevant = any(k in text_for_relevance or k in title.lower() or k in canonical.lower() for k in KEYWORDS)
            if relevant:
                results.append({"url": canonical, "title": title, "seed_id": seed_id, "depth": depth})

            if depth < max_depth:
                for link in links:
                    if link not in seen and is_allowed(link):
                        queue.append((link, depth + 1, seed_id))
    return dedupe_results(results)


def dedupe_results(results: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    for item in results:
        url = item["url"]
        if url not in by_url or item.get("depth", 99) < by_url[url].get("depth", 99):
            by_url[url] = item
    return sorted(by_url.values(), key=lambda x: (x.get("depth", 99), x.get("title", "")))


def canonicalize(url: str) -> str:
    url, _fragment = urldefrag(url)
    return url.strip()


def is_allowed(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host in ALLOWED_DOMAINS


def save_discovered(results: list[dict], out_path: str | Path) -> None:
    Path(out_path).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
