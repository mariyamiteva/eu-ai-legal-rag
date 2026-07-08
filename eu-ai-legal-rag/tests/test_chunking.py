from eu_legal_rag.chunking import split_into_legal_sections, split_with_overlap


def test_split_into_legal_sections_detects_articles():
    text = "Intro\n\nArticle 1\nPurpose\n" + "a" * 600 + "\n\nArticle 2\nDefinitions\n" + "b" * 600
    sections = split_into_legal_sections(text)
    assert len(sections) >= 2
    assert any("Article 1" in s for s in sections)
    assert any("Article 2" in s for s in sections)


def test_split_with_overlap_keeps_text():
    text = "x" * 1000
    chunks = split_with_overlap(text, size=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
