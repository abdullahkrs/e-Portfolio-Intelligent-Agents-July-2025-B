# aro_agent/agents/coordinator.py
from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, UTC

from ..utils.logging import RunLogger
from .. import __version__
from ..models import Record  # <-- moved here

from .discovery import DiscoveryAgent
from .fetch import FetchAgent
from .extract import ExtractAgent
from .storage import StorageAgent
import json
import platform
import sys
import csv






class CoordinatorAgent:
    """
    The "Intention" executor: orchestrates discovery → fetch → extract → store,
    handles basic fault tolerance and deduplication by DOI / arXiv ID.
    """

    def _primary_id_from_row(self, r: dict) -> str | None:
        """
        Extracts and normalizes a primary identifier from a row dictionary.

        Prefers DOI (normalized, lowercased, without https://doi.org/); else arxiv:{id}.
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

    def _find_previous_run_dir(self, query: str, current_run_dir: Path) -> Path | None:
        """
        Finds the most recent run directory (excluding the current one) with the same query.

        Args:
            query (str): The query string to match against previous runs.
            current_run_dir (Path): The path to the current run directory, to be excluded from the search.

        Returns:
            Path | None: The path to the most recent matching run directory, or None if no match is found.
        """
        root = self.run_root
        if not root.exists():
            return None
        candidates: list[tuple[float, Path]] = []
        for d in root.iterdir():
            if not d.is_dir():
                continue
            if d == current_run_dir:
                continue
            if not d.name.startswith("run_"):
                continue
            # read run.json and match query
            rj = d / "run.json"
            if not rj.exists():
                continue
            try:
                with rj.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
                if (meta.get("query") or "").strip() == query.strip():
                    candidates.append((d.stat().st_mtime, d))
            except Exception:
                continue
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _write_diff_csv(self, *, current_json: Path, previous_json: Path, out_csv: Path) -> int:
        """
        Creates a CSV file containing rows present in the current JSON file but not in the previous JSON file, based on primary_id.

        Args:
            current_json (Path): Path to the current JSON file.
            previous_json (Path): Path to the previous JSON file.
            out_csv (Path): Path where the diff CSV file will be written.

        Returns:
            int: The number of new rows written to the CSV file.
        """
        try:
            with current_json.open("r", encoding="utf-8") as f:
                cur_rows = json.load(f) or []
        except Exception:
            cur_rows = []

        try:
            with previous_json.open("r", encoding="utf-8") as f:
                prev_rows = json.load(f) or []
        except Exception:
            prev_rows = []

        # Build ID sets (compute if absent)
        def _pid(row: dict) -> str | None:
            return row.get("primary_id") or self._primary_id_from_row(row)

        prev_ids = {pid for pid in (_pid(r) for r in prev_rows) if pid}
        new_rows = [r for r in cur_rows if (_pid(r) not in prev_ids)]

        # Choose header: prefer current row keys + ensure primary_id first
        header = []
        if cur_rows:
            header = list(cur_rows[0].keys())
            if "primary_id" not in header:
                header.insert(0, "primary_id")
            else:
                # move to front
                header = ["primary_id"] + [h for h in header if h != "primary_id"]
        else:
            header = ["primary_id","source","doi","arxiv_id","title","authors","abstract","published","url","venue","pdf_url","license"]

        # Write CSV
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in new_rows:
                row = dict(r)
                if "primary_id" not in row or not row["primary_id"]:
                    row["primary_id"] = self._primary_id_from_row(row)
                # join authors for readability
                if isinstance(row.get("authors"), list):
                    row["authors"] = "; ".join(a for a in row["authors"] if a)
                w.writerow(row)

        return len(new_rows)

    def _bdi_log(self, logger, trace: list[dict], phase: str, **payload):
        """
        Logs Belief-Desire-Intention (BDI) events for debugging and analysis.

        Args:
            logger: The logger instance to use for logging.
            trace: A list to append the event to, for a complete history.
            phase: The BDI phase ("belief", "desire", "intention", "plan", or "result").
            **payload: Keyword arguments containing the event-specific data.
        """
        from datetime import datetime, UTC  # keep local if not imported at top
        evt = {
            "ts": datetime.now(UTC).isoformat(),
            "phase": phase,
            **payload,
        }
        trace.append(evt)
        logger.info(f"bdi_{phase}", **payload)

    def __init__(
        self,
        contact_email: str,
        timeout: float = 15.0,
        enable_sources: Dict[str, bool] | None = None,
        run_root: Path | None = None,          # ← add this parameter
    ):
        """
        Initializes the CoordinatorAgent.

        Args:
            contact_email: Email address for API usage, passed to sub-agents.
            timeout: Timeout for API requests in seconds.
            enable_sources: A dictionary specifying which data sources to enable (e.g., {"arxiv": True, "crossref": True}).
            run_root:  The root directory for storing run data; defaults to "out" or the ARO_OUT_ROOT environment variable.
        """
        self.contact_email = contact_email
        self.timeout = timeout
        self.enable_sources = enable_sources or {"arxiv": True, "crossref": True, "doaj": True}
        # prefer explicit arg, then env var, then default "out"
        self.run_root = Path(
            run_root
            or os.environ.get("ARO_OUT_ROOT", "out")
        ).resolve()

    def _write_manifest(self, run_dir: Path, *, query: str, per_source_limit: int,
                    from_year: int | None, to_year: int | None,
                    artefacts: Dict[str, str], counts: Dict[str, int]) -> None:
        """
        Writes a reproducibility manifest describing this run.

        Args:
            run_dir (Path): The directory where the run data is stored.
            query (str): The search query used for the run.
            per_source_limit (int): The maximum number of records to fetch from each data source.
            from_year (int | None): The starting year for filtering records.
            to_year (int | None): The ending year for filtering records.
            artefacts (Dict[str, str]): Paths to the generated artefacts (e.g., CSV, JSON files).
            counts (Dict[str, int]): Counts of records at various stages of processing.
        """
        manifest = {
            "version": __version__,
            "timestamp": datetime.now(UTC).isoformat(),
            "query": query,
            "per_source_limit": per_source_limit,
            "from_year": from_year,
            "to_year": to_year,
            "sources_enabled": self.enable_sources,
            "counts": counts,                      # e.g., fetched vs. deduped
            "artefacts": artefacts,                # paths to csv/json/sqlite/bib
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
            },
        }
        path = run_dir / "run.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)


    def run(self, query: str, per_source_limit: int = 50, from_year: int | None = None, to_year: int | None = None) -> Dict[str, Any]:
        """
        Executes the data collection and processing pipeline.

        Args:
            query: The search query to use for discovering relevant records.
            per_source_limit: The maximum number of records to fetch from each data source.
            from_year:  Filter results to include only records published on or after this year.
            to_year: Filter results to include only records published on or before this year.

        Returns:
            A dictionary containing paths to the generated artefacts (e.g., CSV, JSON files).
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        run_dir = self.run_root / f"run_{timestamp}"     # <- single source of truth
        run_dir.mkdir(parents=True, exist_ok=True)
        logger = RunLogger(run_dir)

        logger.info("run_start", query=query, per_source_limit=per_source_limit, run_dir=str(run_dir))
        bdi_trace: list[dict] = []
        self._bdi_log(logger, bdi_trace, "desire", desire={
            "goal": "collect_metadata",
            "query": query,
            "per_source_limit": per_source_limit,
        })


        # 1) Discover API calls
        discovery = DiscoveryAgent(contact_email=self.contact_email)
        tasks = discovery.plan(
            query,
            per_source_limit,
            self.enable_sources,
            from_year=from_year,
            to_year=to_year,
        )

        # --- Tiny contract-net style bids (log only) ---
        bids = []
        for src, spec in tasks.items():
            est_pages = 1
            if isinstance(spec, list):
                est_pages = len(spec)
            elif isinstance(spec, dict) and isinstance(spec.get("paginate"), dict):
                pg = spec["paginate"]
                page_size = pg.get("rows") or pg.get("page_size") or 100
                limit = pg.get("limit") or per_source_limit
                try:
                    est_pages = max(1, int((int(limit) + int(page_size) - 1) // int(page_size)))
                except Exception:
                    est_pages = 1
            bids.append({"source": src, "estimated_pages": est_pages})

        # pick the "best" (fewest pages) first purely for logging (we still fetch all)
        bids_sorted = sorted(bids, key=lambda b: b["estimated_pages"])
        self._bdi_log(logger, bdi_trace, "plan", plan={"action":"ContractNetBids","bids":bids_sorted})


        logger.info("discovery_planned", tasks=tasks)
        self._bdi_log(logger, bdi_trace, "intention", intention={
            "plan": "SearchAcrossSources",
            "sources": [k for k, v in self.enable_sources.items() if v],
            # works if tasks is dict of lists or dict of single specs:
            "task_count": (sum(len(v) for v in tasks.values()) 
                        if tasks and isinstance(next(iter(tasks.values()), None), list) 
                        else len(tasks)),
        })


        # 2) Fetch raw responses
        fetcher = FetchAgent(contact_email=self.contact_email, timeout=self.timeout)
        raw_blobs = fetcher.execute(tasks)
        logger.info("fetch_done", sources=list(raw_blobs.keys()))
        self._bdi_log(logger, bdi_trace, "belief", belief={
            "observation": "network_fetch_complete",
            "sources_with_payload": [k for k, v in raw_blobs.items() if v],
        })


        # 3) Extract normalised records
        extractor = ExtractAgent()
        records: List[Record] = extractor.process(raw_blobs)
        logger.info("extract_done", count=len(records))
        def _year_ok(published: str | None) -> bool:
            """
            Helper function to determine if a record's publication year falls within the specified range.

            Args:
                published: The publication date string of the record.

            Returns:
                True if the year is within the range or if no range is specified, False otherwise.
            """
            if not (from_year or to_year):
                return True
            if not published or len(published) < 4 or not published[:4].isdigit():
                # if you prefer to KEEP undated items, return True here instead
                return False
            y = int(published[:4])
            if from_year is not None and y < from_year:
                return False
            if to_year is not None and y > to_year:
                return False
            return True
        
        records = [r for r in records if _year_ok(r.published)]
        logger.info("year_filter", from_year=from_year, to_year=to_year, count=len(records))
        self._bdi_log(logger, bdi_trace, "belief", belief={
            "observation": "extraction_complete",
            "record_count": len(records),
        })

        
        # 4) Deduplicate (DOI first, arXiv fallback)
        dedup = {}
        for r in records:
            key = r.doi or (f"arxiv:{r.arxiv_id}" if r.arxiv_id else None)
            if key and key not in dedup:
                dedup[key] = r
        final = list(dedup.values())
        self._bdi_log(logger, bdi_trace, "plan", plan={
            "action": "Deduplicate",
            "before": len(records),
            "after": len(final),
            "key": "doi→arxiv",
        })


        # 5) Store
        storage = StorageAgent(run_dir=run_dir, logger=logger)
        artefacts = storage.save_all(final, query=query)

        # Produce diff.csv vs. previous run (same query), if available
        diff_path: Path | None = None
        try:
            prev_dir = self._find_previous_run_dir(query, run_dir)
            if prev_dir:
                prev_json = prev_dir / "results.json"
                cur_json = Path(artefacts.get("json"))
                if prev_json.exists() and cur_json and cur_json.exists():
                    diff_path = run_dir / "diff.csv"
                    new_count = self._write_diff_csv(current_json=cur_json, previous_json=prev_json, out_csv=diff_path)
                    # Optional: log as BDI result detail
                    self._bdi_log(logger, bdi_trace, "plan", plan={
                        "action": "DiffWithPreviousRun",
                        "previous_run": str(prev_dir.name),
                        "new_items": new_count,
                    })
                    # expose in artefacts
                    artefacts["diff_csv"] = str(diff_path)
        except Exception as e:
            logger.info("diff_failed", error=str(e))

        # Prepare minimal counts for reproducibility
        # after extraction, before filtering:
        extracted_count = len(records)

        # apply year filter
        records = [r for r in records if _year_ok(r.published)]

        # later, after dedupe
        counts = {"fetched": extracted_count, "filtered": len(records), "deduped": len(final)}


        self._bdi_log(logger, bdi_trace, "result", result={
            "artefacts": artefacts,
            "counts": counts,
        })

        # Persist BDI trace alongside run.json
        with (run_dir / "bdi_trace.json").open("w", encoding="utf-8") as f:
            json.dump(bdi_trace, f, ensure_ascii=False, indent=2)

        # Write manifest to run folder
        self._write_manifest(
            run_dir,
            query=query,
            per_source_limit=per_source_limit,
            from_year=from_year,
            to_year=to_year,
            artefacts=artefacts,
            counts=counts,
        )


        logger.info("run_end", artefacts=artefacts)
        return artefacts


