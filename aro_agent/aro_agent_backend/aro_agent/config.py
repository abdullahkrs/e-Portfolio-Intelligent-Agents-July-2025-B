from __future__ import annotations

# API endpoints and User-Agent
ARXIV_API = "http://export.arxiv.org/api/query"           # Atom XML
"""The base URL for the arXiv API."""
CROSSREF_API = "https://api.crossref.org/works"           # JSON
"""The base URL for the Crossref API."""
DOAJ_API = "https://doaj.org/api/v2/search/articles/"     # JSON (v2)
"""The base URL for the DOAJ API."""

DEFAULT_USER_AGENT = "aro-agent/0.1 (+https://example.org/contact; mailto:{email})"
"""The default User-Agent string used for API requests."""
REQUESTS_PER_SOURCE = 1  # Basic rate pacing per execution step (tunable)
"""The number of requests allowed per source in each execution step (tunable for rate limiting)."""
MAX_PER_SOURCE_DEFAULT = 50
"""The default maximum number of items to retrieve from each source."""
