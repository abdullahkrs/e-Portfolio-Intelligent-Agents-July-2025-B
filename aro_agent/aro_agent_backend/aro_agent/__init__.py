"""
Academic Research Online Agent (aro-agent)

A lightweight, API-first, multi-agent system that retrieves academic
metadata from arXiv, Crossref, and DOAJ, normalises identifiers, and
exports CSV/JSON/SQLite with a simple HTML results page.

BDI Mapping (high-level):
- Beliefs   = Stored metadata (in-memory list + SQLite) and run logs
- Desires   = User goal (e.g., "retrieve N results for a query")
- Intentions= Concrete plan (discovery → fetch → extract → store)

This package is intentionally minimal and standard-library-first.
"""
__all__ = ["agents"]
__version__ = "0.1.0"
