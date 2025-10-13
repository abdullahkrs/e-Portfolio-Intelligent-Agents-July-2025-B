from __future__ import annotations
from typing import Dict, List
from dataclasses import dataclass
from xml.etree import ElementTree as ET
import json

from ..utils.normalise import normalise_doi, extract_arxiv_id
from ..models import Record

def _iso_date_from_crossref_dateparts(issued_obj) -> str | None:
    """
    Extracts an ISO-formatted date string from Crossref's date parts structure.

    Crossref dates look like: {"date-parts": [[2023, 5, 1]]}.
    Some records may have missing or null parts; this function is defensive.

    Args:
        issued_obj (dict): A dictionary containing the "date-parts" key with date information.

    Returns:
        str | None: An ISO-formatted date string (YYYY-MM-DD, YYYY-MM, or YYYY), or None if extraction fails.
    """
    if not isinstance(issued_obj, dict):
        return None
    parts = issued_obj.get("date-parts")
    if not parts or not isinstance(parts, list) or not parts[0] or not isinstance(parts[0], list):
        return None

    dp = parts[0]
    try:
        y = int(dp[0]) if len(dp) >= 1 and dp[0] is not None else None
        m = int(dp[1]) if len(dp) >= 2 and dp[1] is not None else None
        d = int(dp[2]) if len(dp) >= 3 and dp[2] is not None else None
    except (ValueError, TypeError):
        return None

    if y is None:
        return None

    s = f"{y:04d}"
    if m is not None:
        s += f"-{m:02d}"
        if d is not None:
            s += f"-{d:02d}"
    return s


class ExtractAgent:
    """
    Parses raw responses from various sources into a common Record structure.
    (Transforms environment perceptions into "Beliefs")
    """

    def process(self, raw_blobs: Dict[str, str | list[str]]) -> List[Record]:
        """
        Processes raw data blobs from different sources and extracts relevant information into a list of Record objects.

        Args:
            raw_blobs (Dict[str, str | list[str]]): A dictionary where keys are source names (e.g., "arxiv", "crossref")
                                                    and values are the raw data (either a string or a list of strings).

        Returns:
            List[Record]: A list of Record objects, each representing a parsed metadata record.
        """
        out: List[Record] = []
        def _each(x):
            if isinstance(x, list): 
                return x
            return [x]

        if raw_blobs.get("arxiv"):
            for chunk in _each(raw_blobs["arxiv"]):
                out.extend(self._from_arxiv(chunk))

        if raw_blobs.get("crossref"):
            for chunk in _each(raw_blobs["crossref"]):
                out.extend(self._from_crossref(chunk))

        if raw_blobs.get("doaj"):
            for chunk in _each(raw_blobs["doaj"]):
                out.extend(self._from_doaj(chunk))
        return out


    # ---- arXiv (Atom XML) ----
    def _from_arxiv(self, xml_text: str) -> List[Record]:
        """
        Extracts metadata records from an arXiv API response (Atom XML format).

        Args:
            xml_text (str): The XML content from the arXiv API.

        Returns:
            List[Record]: A list of Record objects extracted from the XML.
        """
        if not xml_text.strip():
            return []
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        records: List[Record] = []
        for entry in root.findall('atom:entry', ns):
            title = (entry.findtext('atom:title', default="", namespaces=ns) or "").strip()
            summary = (entry.findtext('atom:summary', default="", namespaces=ns) or "").strip()
            published = (entry.findtext('atom:published', default="", namespaces=ns) or "").strip()
            id_url = (entry.findtext('atom:id', default="", namespaces=ns) or "").strip()
            arxiv_id = extract_arxiv_id(id_url)

            # DOI may appear as <arxiv:doi>
            doi = None
            doi_el = entry.find('arxiv:doi', ns)
            if doi_el is not None and doi_el.text:
                doi = normalise_doi(doi_el.text)

            authors = []
            for a in entry.findall('atom:author', ns):
                name = a.findtext('atom:name', default="", namespaces=ns)
                if name:
                    authors.append(name)

            pdf_url = None
            for link in entry.findall('atom:link', ns):
                if link.get('type') == 'application/pdf':
                    pdf_url = link.get('href')
                    break

            url = id_url or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None)

            r = Record(
                source="arxiv",
                doi=doi,
                arxiv_id=arxiv_id,
                title=title or None,
                authors=authors,
                abstract=summary or None,
                published=published or None,
                url=url,
                venue="arXiv",
                pdf_url=pdf_url,
                license=None,
            )
            records.append(r)
        return records

    # ---- Crossref (JSON) ----
    def _from_crossref(self, json_text: str) -> List[Record]:
        """
        Extracts metadata records from a Crossref API response (JSON format).

        Args:
            json_text (str): The JSON content from the Crossref API.

        Returns:
            List[Record]: A list of Record objects extracted from the JSON.
        """
        if not json_text.strip():
            return []
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return []
        items = (data.get("message") or {}).get("items") or []
        records: List[Record] = []
        for it in items:
            doi = normalise_doi(it.get("DOI"))
            title_list = it.get("title") or []
            title = title_list[0] if title_list else None

            authors = []
            for a in it.get("author") or []:
                parts = [a.get("given"), a.get("family")]
                authors.append(" ".join([p for p in parts if p]))

            published = None
            issued = it.get("issued") or it.get("created") or {}
            published = _iso_date_from_crossref_dateparts(issued)

            url = it.get("URL")
            venue_list = it.get("container-title") or []
            venue = venue_list[0] if venue_list else None

            # license may be a list of dicts with 'URL' or 'content-version'
            lic = None
            if isinstance(it.get("license"), list) and it["license"]:
                lic = it["license"][0].get("URL") or it["license"][0].get("content-version")

            r = Record(
                source="crossref",
                doi=doi,
                arxiv_id=None,
                title=title,
                authors=authors,
                abstract=None,  # Crossref often doesn't carry abstracts
                published=published,
                url=url,
                venue=venue,
                pdf_url=None,
                license=lic,
            )
            records.append(r)
        return records

    # ---- DOAJ (JSON) ----
    def _from_doaj(self, json_text: str) -> List[Record]:
        """
        Extracts metadata records from a DOAJ API response (JSON format).

        Args:
            json_text (str): The JSON content from the DOAJ API.

        Returns:
            List[Record]: A list of Record objects extracted from the JSON.
        """
        if not json_text.strip():
            return []
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return []

        # DOAJ v2 returns {"results":[{...},{...}]}
        results = data.get("results") or []
        records: List[Record] = []
        for it in results:
            # Typical structure: it["bibjson"] contains metadata
            bj = it.get("bibjson") or {}
            title = bj.get("title")
            doi = normalise_doi((bj.get("identifier") or [{}])[0].get("id") if bj.get("identifier") else None)

            authors = []
            for a in bj.get("author") or []:
                name = a.get("name")
                if name:
                    authors.append(name)

            pub = bj.get("year")
            published = str(pub) if pub else None

            url = None
            if bj.get("link"):
                for ln in bj["link"]:
                    if ln.get("type") == "fulltext":
                        url = ln.get("url") or url

            venue = (bj.get("journal") or {}).get("title")

            r = Record(
                source="doaj",
                doi=doi,
                arxiv_id=None,
                title=title,
                authors=authors,
                abstract=None,  # DOAJ API may carry abstracts but often not uniformly
                published=published,
                url=url,
                venue=venue,
                pdf_url=None,
                license=None,
            )
            records.append(r)
        return records
