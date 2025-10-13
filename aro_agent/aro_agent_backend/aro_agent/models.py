# aro_agent/models.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Record:
    """
    Represents a metadata record extracted from a data source.
    """
    source: str
    """The source of the record (e.g., "arxiv", "crossref")."""
    doi: str | None
    """The Digital Object Identifier (DOI) of the record, if available."""
    arxiv_id: str | None
    """The arXiv ID of the record, if available."""
    title: str | None
    """The title of the record."""
    authors: list[str]
    """A list of author names for the record."""
    abstract: str | None
    """The abstract or summary of the record."""
    published: str | None  # ISO date
    """The publication date of the record in ISO format (YYYY-MM-DD or YYYY-MM or YYYY)."""
    url: str | None
    """The URL to the record's landing page."""
    venue: str | None      # journal or container/title
    """The venue where the record was published (e.g., journal name, conference proceedings)."""
    pdf_url: str | None
    """The URL to the PDF version of the record, if available."""
    license: str | None
    """The license information for the record, if available."""
