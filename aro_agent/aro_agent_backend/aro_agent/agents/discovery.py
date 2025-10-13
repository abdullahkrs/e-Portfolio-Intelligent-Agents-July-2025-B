from __future__ import annotations
from typing import Dict, Any
import urllib.parse as ul
from .. import __version__
from ..utils.normalise import normalise_doi
from ..config import ARXIV_API, CROSSREF_API, DOAJ_API, DEFAULT_USER_AGENT

class DiscoveryAgent:
    """
    Translates a free-text query into concrete API calls per source.
    (Represents the "Desire" shaping into a plan of actions)
    """
    def __init__(self, contact_email: str):
        """
        Initializes the DiscoveryAgent with a contact email.

        Args:
            contact_email (str): Email address for API usage, included in User-Agent header.
        """
        self.contact_email = contact_email

    def user_agent(self) -> str:
        """
        Generates a User-Agent string including the contact email.

        Returns:
            str: User-Agent string.
        """
        return DEFAULT_USER_AGENT.format(email=self.contact_email)

    def plan(
        self,
        query: str,
        per_source_limit: int,
        enable_sources: Dict[str, bool],
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> Dict[str, Any]:
        """
        Generates a plan of API calls for each enabled data source based on the query and constraints.

        Args:
            query (str): The search query string.
            per_source_limit (int): The maximum number of results to retrieve from each source.
            enable_sources (Dict[str, bool]): A dictionary specifying which data sources to enable (e.g., {"arxiv": True, "crossref": True}).
            from_year (int | None): Filter results to include only records published on or after this year.
            to_year (int | None): Filter results to include only records published on or before this year.

        Returns:
            Dict[str, Any]: A dictionary containing the API call specifications for each enabled source.
        """

        q = query.strip()
        page_size = min(per_source_limit, 100)  # Crossref up to 100 rows
        pages = max(1, (per_source_limit + page_size - 1) // page_size)

        tasks: Dict[str, Any] = {}

        if enable_sources.get("crossref", True):
            """
            Configures the Crossref API call.
            """
            # Build an optional Crossref filter string for year bounds
            cr_filter_parts = []
            if from_year:
                cr_filter_parts.append(f"from-pub-date:{int(from_year)}-01-01")
            if to_year:
                cr_filter_parts.append(f"until-pub-date:{int(to_year)}-12-31")
            cr_filter = ",".join(cr_filter_parts) if cr_filter_parts else None

            params = {
                "query": q,
                "select": "DOI,title,author,container-title,issued,URL,license",
                # 'cursor' and 'rows' are handled by FetchAgent via paginate
            }
            if cr_filter:
                params["filter"] = cr_filter

            tasks["crossref"] = {
                "url": CROSSREF_API,            # e.g., "https://api.crossref.org/works"
                "params": params,
                "headers": {"User-Agent": self.user_agent()},
                "paginate": {
                    "strategy": "crossref",
                    "limit": int(per_source_limit),
                    "rows": 100,                # per-page size
                    "max_pages": 50             # safety cap
                }
            }




        if enable_sources.get("arxiv", True):
            """
            Configures the ArXiv API call.
            """
            # Optional: build a year filter via query terms (arXiv doesn’t have a clean year param)
            # You can leave it out or add additional terms to search_query.
            params = {
                "search_query": f"all:{q}",
                "sortBy": "submittedDate", "sortOrder": "descending",  # optional
            }

            tasks["arxiv"] = {
                "url": ARXIV_API,               # e.g., "https://export.arxiv.org/api/query"
                "params": params,
                "headers": {"User-Agent": self.user_agent()},
                "paginate": {
                    "strategy": "arxiv",
                    "limit": int(per_source_limit),
                    "page_size": 100,
                    "max_pages": 50
                }
            }



        if enable_sources.get("doaj", True):
            """
            Configures the DOAJ API call.
            """
            tasks["doaj"] = {
                "url": DOAJ_API + ul.quote(q),     # e.g., "https://doaj.org/api/v2/search/articles?q="
                "params": {
                    # page/pageSize handled by FetchAgent
                },
                "headers": {"User-Agent": self.user_agent()},
                "paginate": {
                    "strategy": "doaj",
                    "limit": int(per_source_limit),
                    "page_size": 100,
                    "max_pages": 50
                }
            }



        return tasks

