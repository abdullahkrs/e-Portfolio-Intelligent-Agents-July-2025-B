from __future__ import annotations
from typing import Dict, Any, List
import json, re

from ..utils.http import http_get
import concurrent.futures as _fut

# ---------- Helpers ----------

def _default_headers(contact_email: str) -> Dict[str, str]:
    """
    Be a good API citizen: identify your client + contact email.
    """
    ua = f"aro-agent/1 (+mailto:{contact_email})"
    return {
        "User-Agent": ua,
        "Accept": "application/json,text/plain;q=0.9,*/*;q=0.1",
    }

def _append(blobs: Dict[str, List[str]], key: str, text: str) -> None:
    """
    Appends text to a list of strings in a dictionary.

    If the key does not exist or the value is not a list, it initializes an empty list.

    Args:
        blobs (Dict[str, List[str]]): The dictionary to append to.
        key (str): The key to append the text to.
        text (str): The text to append.
    """
    if key not in blobs or not isinstance(blobs[key], list):
        blobs[key] = []
    blobs[key].append(text)

# ---------- Optional pagination strategies ----------

def _paginate_crossref(spec: Dict[str, Any], contact_email: str, timeout: float) -> List[str]:
    """
    Paginates through the Crossref API to retrieve multiple pages of results.

    Args:
        spec (Dict[str, Any]): The API call specification, including URL, parameters, and pagination settings.
        contact_email (str): Email address for API usage, included in User-Agent header.
        timeout (float): Timeout for API requests in seconds.

    Returns:
        List[str]: A list of raw text responses from the API.
    """
    out: List[str] = []
    params = dict(spec.get("params") or {})
    pconf = dict(spec.get("paginate") or {})
    limit = int(pconf.get("limit", 200))
    rows  = int(pconf.get("rows", 100))
    params["rows"] = rows
    params["cursor"] = params.get("cursor") or "*"

    headers = dict(_default_headers(contact_email))
    headers.update(spec.get("headers") or {})

    fetched = 0
    max_pages = int(pconf.get("max_pages", 100))

    for _ in range(max_pages):
        status, txt, hdrs = http_get(spec["url"], params=params, headers=headers, timeout=timeout)
        if status != 200 or not txt:
            break

        try:
            j = json.loads(txt)
            items = j.get("message", {}).get("items", [])
            next_cursor = j.get("message", {}).get("next-cursor")
        except Exception:
            items, next_cursor = [], None

        out.append(txt)
        fetched += len(items)

        if not items or fetched >= limit or not next_cursor:
            break

        params["cursor"] = next_cursor

    return out

def _paginate_doaj(spec: Dict[str, Any], contact_email: str, timeout: float) -> List[str]:
    """
    Paginates through the DOAJ API to retrieve multiple pages of results.

    Args:
        spec (Dict[str, Any]): The API call specification, including URL, parameters, and pagination settings.
        contact_email (str): Email address for API usage, included in User-Agent header.
        timeout (float): Timeout for API requests in seconds.

    Returns:
        List[str]: A list of raw text responses from the API.
    """
    out: List[str] = []
    params = dict(spec.get("params") or {})
    pconf = dict(spec.get("paginate") or {})
    limit = int(pconf.get("limit", 200))
    page_size = int(pconf.get("page_size", 100))
    params["pageSize"] = page_size
    page = int(params.get("page", 1))

    headers = dict(_default_headers(contact_email))
    headers.update(spec.get("headers") or {})

    fetched = 0
    max_pages = int(pconf.get("max_pages", 200))

    for _ in range(max_pages):
        params["page"] = page
        status, txt, hdrs = http_get(spec["url"], params=params, headers=headers, timeout=timeout)
        if status != 200 or not txt:
            break

        try:
            j = json.loads(txt)
            results = j.get("results", [])
        except Exception:
            results = []

        out.append(txt)
        fetched += len(results)

        if not results or fetched >= limit:
            break

        page += 1

    return out

def _paginate_arxiv(spec: Dict[str, Any], contact_email: str, timeout: float) -> List[str]:
    """
    Paginates through the ArXiv API to retrieve multiple pages of results.

    Args:
        spec (Dict[str, Any]): The API call specification, including URL, parameters, and pagination settings.
        contact_email (str): Email address for API usage, included in User-Agent header.
        timeout (float): Timeout for API requests in seconds.

    Returns:
        List[str]: A list of raw text responses from the API.
    """
    out: List[str] = []
    params = dict(spec.get("params") or {})
    pconf = dict(spec.get("paginate") or {})
    limit = int(pconf.get("limit", 200))
    page_size = int(pconf.get("page_size", 100))
    params["max_results"] = page_size
    start = int(params.get("start", 0))

    headers = dict(_default_headers(contact_email))
    headers.update(spec.get("headers") or {})

    fetched = 0
    max_pages = int(pconf.get("max_pages", 200))

    for _ in range(max_pages):
        params["start"] = start
        status, txt, hdrs = http_get(spec["url"], params=params, headers=headers, timeout=timeout)
        if status != 200 or not txt:
            break

        count_entries = len(re.findall(r"<entry[ >]", txt))
        out.append(txt)
        fetched += count_entries

        if count_entries == 0 or fetched >= limit:
            break

        start += page_size

    return out

# ---------- Fetch Agent ----------

class FetchAgent:
    """
    Executes API requests with retry logic and returns raw texts keyed by source.
    Use `paginate` in a task to enable multi-page fetch:

        tasks["crossref"] = {
          "url": "https://api.crossref.org/works",
          "params": {"query": "..."},
          "paginate": {"strategy": "crossref", "limit": 500, "rows": 100, "max_pages": 50}
        }

    If you don't set `paginate`, behavior stays single-request per source (as before).
    """
    def __init__(self, contact_email: str, timeout: float = 15.0):
        """
        Initializes the FetchAgent.

        Args:
            contact_email (str): Email address for API usage, included in User-Agent header.
            timeout (float): Timeout for API requests in seconds.
        """
        self.contact_email = contact_email
        self.timeout = timeout

    def execute(self, tasks: Dict[str, Any]) -> Dict[str, list[str] | str]:
        """
        Executes the API requests defined in the tasks and returns the raw responses.

        Args:
            tasks (Dict[str, Any]): A dictionary where keys are source names (e.g., "arxiv", "crossref")
                                    and values are the API call specifications.

        Returns:
            Dict[str, list[str] | str]: A dictionary where keys are source names and values are the raw
                                        text responses (either a string or a list of strings).
        """
        blobs: Dict[str, list[str] | str] = {}
        for source, spec in tasks.items():

            # If discovery already produced a list of page-specs, fetch each one
            import concurrent.futures as _fut

            if isinstance(spec, list):
                parts: List[str] = []

                def _one(s):
                    headers = dict(_default_headers(self.contact_email))
                    headers.update(s.get("headers") or {})
                    status, txt, _ = http_get(
                        s["url"],
                        params=s.get("params"),
                        headers=headers,
                        timeout=self.timeout
                    )
                    return (status, txt)

                # Fetch up to 8 pages in parallel (tune as needed)
                with _fut.ThreadPoolExecutor(max_workers=min(8, len(spec))) as pool:
                    for status, txt in pool.map(_one, spec):
                        if status == 200 and txt:
                            parts.append(txt)
                blobs[source] = parts
                continue


            # Strategy-specific pagination if provided
            pconf = spec.get("paginate")
            if isinstance(pconf, dict) and "strategy" in pconf:
                strat = pconf["strategy"]
                if strat == "crossref":
                    blobs[source] = _paginate_crossref(spec, self.contact_email, self.timeout)
                    continue
                if strat == "doaj":
                    blobs[source] = _paginate_doaj(spec, self.contact_email, self.timeout)
                    continue
                if strat == "arxiv":
                    blobs[source] = _paginate_arxiv(spec, self.contact_email, self.timeout)
                    continue
                # Unknown strategy → fall back to single shot

            # Single-shot (legacy behavior), but with polite headers + retries
            headers = dict(_default_headers(self.contact_email))
            headers.update(spec.get("headers") or {})
            status, txt, _ = http_get(
                spec["url"],
                params=spec.get("params"),
                headers=headers,
                timeout=self.timeout
            )
            blobs[source] = txt if status == 200 else ""

        return blobs
