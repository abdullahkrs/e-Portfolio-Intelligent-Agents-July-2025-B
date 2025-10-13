from __future__ import annotations
import csv, json, sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..models import Record

def _bibtex_entry(i: int, r: dict) -> str:
    """
    Generates a BibTeX entry from a record dictionary.

    Args:
        i (int): Index of the record (used for generating a unique key if DOI/arXiv ID is missing).
        r (dict): A dictionary containing record data (title, authors, year, venue, doi, url).

    Returns:
        str: A BibTeX-formatted string representing the record.
    """
    key = (r.get("doi") or r.get("arxiv_id") or f"key{i}").replace("/", "_")
    authors = r.get("authors")
    if isinstance(authors, list):
        authors = " and ".join(a for a in authors if a)
    title = (r.get("title") or "").replace("{","").replace("}","")
    year = (r.get("published") or "")[:4]
    venue = r.get("venue") or ""
    # Choose entry type by source (rough heuristic)
    entry_type = "article" if venue else "misc"
    lines = [
        f"@{entry_type}{{{key},",
        f"  title = {{{title}}},",
        f"  author = {{{authors or ''}}},",
        f"  year = {{{year}}},",
    ]
    if venue: lines.append(f"  journal = {{{venue}}},")
    if r.get("doi"): lines.append(f"  doi = {{{r['doi']}}},")
    if r.get("url"): lines.append(f"  url = {{{r['url']}}},")
    lines.append("}")
    return "\n".join(lines)

class StorageAgent:
    """
    Persists results to CSV, JSON, and SQLite; generates a static HTML view.
    (Embodies the "Beliefs" persistence & presentation)
    """
    
    def __init__(self, run_dir: Path, logger):
        """
        Initializes the StorageAgent with a run directory and a logger.

        Args:
            run_dir (Path): The directory where the run data is stored.
            logger: The logger instance to use for logging.
        """
        self.run_dir = run_dir
        self.logger = logger

    def save_all(self, records: List[Record], query: str) -> Dict[str, Any]:
        """
        Saves the extracted records to various formats (CSV, JSON, SQLite, BibTeX).

        Args:
            records (List[Record]): A list of Record objects to be saved.
            query (str): The search query used to generate these records.

        Returns:
            Dict[str, Any]: A dictionary containing the paths to the saved files.
        """
        data = [asdict(r) for r in records]
        # compute primary_id for each row
        for r in data:
            r["primary_id"] = _primary_id_from_row(r)


        # 1) CSV
        csv_path = self.run_dir / "results.csv"
        self._write_csv(csv_path, data)

        # 2) JSON
        json_path = self.run_dir / "results.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 3) SQLite
        db_path = self.run_dir / "results.sqlite"
        self._write_sqlite(db_path, data)


        # 5) BibTeX
        bib_path = self.run_dir / "results.bib"
        with bib_path.open("w", encoding="utf-8") as f:
            for i, row in enumerate(data):
                f.write(_bibtex_entry(i, row) + "\n\n")


        return {
            "csv": str(csv_path),
            "json": str(json_path),
            "sqlite": str(db_path),
            "bibtex": str(bib_path)
        }

    # ---- helpers ----

    def _write_csv(self, path: Path, rows: List[dict]):
        """
        Writes a list of dictionaries to a CSV file.

        Args:
            path (Path): The path to the CSV file.
            rows (List[dict]): A list of dictionaries, where each dictionary represents a row in the CSV.
        """
        if not rows:
            # still write header
            header = ["primary_id","source","doi","arxiv_id","title","authors","abstract","published","url","venue","pdf_url","license"]
        else:
            header = list(rows[0].keys())
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in rows:
                r2 = dict(r)
                if isinstance(r2.get("authors"), list):
                    r2["authors"] = "; ".join(r2["authors"])
                w.writerow(r2)

    def _write_sqlite(self, db_path: Path, rows: List[dict]):
        """
        Writes a list of dictionaries to an SQLite database.

        Args:
            db_path (Path): The path to the SQLite database file.
            rows (List[dict]): A list of dictionaries, where each dictionary represents a row in the database table.
        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Pragmatic defaults for small, single-writer workloads
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA temp_store=MEMORY;")
        cur.execute("PRAGMA cache_size=-20000;")  # ~20MB page cache

        cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            primary_id TEXT,
            source TEXT,
            doi TEXT,
            arxiv_id TEXT,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            published TEXT,
            url TEXT,
            venue TEXT,
            pdf_url TEXT,
            license TEXT,
            UNIQUE(primary_id)
        );

        """)
        # Helpful indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_records_primary_id ON records(primary_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_records_doi        ON records(doi);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_records_arxiv      ON records(arxiv_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_records_published  ON records(published);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_records_venue      ON records(venue);")

        for r in rows:
            cur.execute("""
                INSERT OR IGNORE INTO records
                (primary_id,source,doi,arxiv_id,title,authors,abstract,published,url,venue,pdf_url,license)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?);
            """, (
                r.get("primary_id"),
                r.get("source"), r.get("doi"), r.get("arxiv_id"),
                r.get("title"),
                "; ".join(r.get("authors", [])) if isinstance(r.get("authors"), list) else r.get("authors"),
                r.get("abstract"), r.get("published"), r.get("url"), r.get("venue"),
                r.get("pdf_url"), r.get("license")
            ))
        conn.commit()
        conn.close()

    def _write_html_view(self, dst_dir: Path, query: str):
        """
        Copies template files and generates a static HTML view of the results.

        Args:
            dst_dir (Path): The destination directory where the HTML view will be created.
            query (str): The search query used to generate these records (injected into the HTML).
        """
        # Copy template files next to results.*
        from pathlib import Path as _P
        tpl_dir = _P(__file__).resolve().parents[1] / "templates"
        for name in ("index.html", "assets/style.css", "assets/app.js"):
            src = tpl_dir / name
            tgt = dst_dir / (name.split("/")[-1] if name.endswith(".html") else name.split("/")[-1])
            if name.endswith(".html"):
                # inject query string
                with src.open("r", encoding="utf-8") as f:
                    html = f.read().replace("{{QUERY}}", query)
                with (dst_dir / "index.html").open("w", encoding="utf-8") as f:
                    f.write(html)
            else:
                # assets: write as base name (style.css, app.js)
                with src.open("r", encoding="utf-8") as f:
                    content = f.read()
                with (dst_dir / src.name).open("w", encoding="utf-8") as f:
                    f.write(content)

def _primary_id_from_row(r: dict) -> str | None:
    """
    Extracts and normalizes a primary identifier from a row dictionary.

    Prefers DOI (normalized, lowercased, without https://doi.org/), else arxiv:{id}.

    Args:
        r (dict): A dictionary containing data fields, expected to include "doi" and/or "arxiv_id".

    Returns:
        str | None: The normalized DOI or arXiv ID if found, otherwise None.
    """
    doi = (r.get("doi") or "").strip().lower()
    if doi.startswith("https://doi.org/"):
        doi = doi.split("https://doi.org/")[1]
    arxiv = (r.get("arxiv_id") or "").strip().lower()
    return doi or (f"arxiv:{arxiv}" if arxiv else None)
