from __future__ import annotations

from io import BytesIO
import re
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import httpx
from pypdf import PdfReader
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential

from .schemas import RawDocument, Source
from .settings import get_settings


PDF_HINTS = (".pdf", "application/pdf")


class FetchError(RuntimeError):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _http_get(url: str) -> httpx.Response:
    settings = get_settings()
    headers = {"User-Agent": settings.user_agent}
    with httpx.Client(follow_redirects=True, timeout=settings.request_timeout_seconds, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response


def fetch_source(source: Source) -> RawDocument:
    response = _http_get(source.url)
    content_type = response.headers.get("content-type", "").split(";")[0].lower()
    is_pdf = content_type == "application/pdf" or urlparse(str(response.url)).path.lower().endswith(".pdf")

    if is_pdf:
        text = extract_pdf_text(response.content)
        parsed_type = "application/pdf"
    else:
        text = extract_html_text(response.text, url=str(response.url))
        parsed_type = content_type or "text/html"

    text = normalize_text(text)
    if len(text) < 500:
        raise FetchError(f"Parsed text is unexpectedly short for {source.id}: {len(text)} chars")

    return RawDocument(source=source, text=text, content_type=parsed_type, fetched_url=str(response.url))


def extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = []
    for idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - keep ingestion resilient
            page_text = f"[Could not extract page {idx + 1}: {exc}]"
        if page_text.strip():
            pages.append(f"\n\n[Page {idx + 1}]\n{page_text}")
    return "\n".join(pages)


def extract_html_text(html: str, url: str) -> str:
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        include_links=True,
        favor_precision=False,
    )
    if extracted and len(extracted) > 1000:
        return extracted

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    body = soup.get_text("\n", strip=True)
    return f"{title}\n\n{body}"


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_many(sources: Iterable[Source]) -> list[RawDocument]:
    documents: list[RawDocument] = []
    failures: list[tuple[str, str]] = []
    for source in sources:
        try:
            documents.append(fetch_source(source))
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures.append((source.id, str(exc)))
    if failures:
        print("Fetch failures:")
        for source_id, error in failures:
            print(f"- {source_id}: {error}")
    return documents
