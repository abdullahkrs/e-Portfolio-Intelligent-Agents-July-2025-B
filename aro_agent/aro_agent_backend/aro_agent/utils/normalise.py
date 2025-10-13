from __future__ import annotations
import re

def normalise_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = doi.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    return doi.lower()

def extract_arxiv_id(url_or_id: str | None) -> str | None:
    if not url_or_id:
        return None
    s = url_or_id.strip()
    # Accept raw ID or URL like https://arxiv.org/abs/YYMM.NNNNN
    m = re.search(r"(\d{4}\.\d{4,5}(v\d+)?)", s)
    if m:
        return m.group(1)
    # Legacy IDs: cs/0112017 etc.
    m = re.search(r"arxiv\.org/(abs|pdf)/([^/?#]+)", s, re.I)
    if m:
        return m.group(2)
    # Fall back to s
    return s
