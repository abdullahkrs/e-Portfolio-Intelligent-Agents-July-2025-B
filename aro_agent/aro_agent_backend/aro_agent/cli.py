from __future__ import annotations
import argparse
import os
from pathlib import Path
from datetime import datetime, UTC
from .utils.email_gmail import send_email  # at top with other imports
from .utils.compress import make_zip
from .agents.coordinator import CoordinatorAgent
from collections import Counter
from .utils.email_format import build_and_send_email



def build_parser() -> argparse.ArgumentParser:
    """
    Builds and returns an argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: An argument parser configured with all the available command-line options.
    """
    p = argparse.ArgumentParser(
        prog="aro-agent",
        description="Academic Research Online Agent (arXiv + Crossref + DOAJ)"
    )
    p.add_argument("--query", "-q", required=True, help="Search query, e.g. 'machine learning for fraud detection'")
    p.add_argument("--limit", "-n", type=int, default=50, help="Maximum items per source (default: 50)")
    p.add_argument("--out", "-o", default="out", help="Output root directory (default: ./out)")
    p.add_argument("--email", default=os.getenv("CROSSREF_MAILTO", "you@example.com"),
                   help="Contact email used in Crossref User-Agent (default from env CROSSREF_MAILTO)")
    p.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds per request (default: 15)")
    p.add_argument("--no-doaj", action="store_true", help="Skip DOAJ source")
    p.add_argument("--no-arxiv", action="store_true", help="Skip arXiv source")
    p.add_argument("--no-crossref", action="store_true", help="Skip Crossref source")
    p.add_argument(
        "--sources",
        help="Comma-separated list of sources to enable (overrides --no-*). "
            "Accepted: arxiv,crossref,doaj. Example: --sources arxiv,crossref",
    )
    p.add_argument("--from-year", type=int, help="Only include items published on/after this year (e.g., 2020)")
    p.add_argument("--to-year", type=int, help="Only include items published on/before this year (e.g., 2025)")
    # in build_parser()
    p.add_argument("--mail-to", help="Email destination(s), comma-separated")
    p.add_argument("--mail-from", help="Sender address (must match the authenticated Gmail account)")
    p.add_argument("--gmail-creds", default="google_client_credentials.json",
                help="Path to Google OAuth client credentials JSON")
    p.add_argument("--gmail-token", default="google_token.json",
                help="Path to write/read the Gmail OAuth token")
    p.add_argument("--no-attach", action="store_true", help="Send email without attachments (links only)")
    p.add_argument("--emit-schedule", action="store_true",
                help="Write a SCHEDULE.txt with OS-specific commands to rerun this query on a schedule.")
    p.add_argument("--schedule", choices=["daily","weekly"], default="weekly",
                help="Frequency to suggest when --emit-schedule is given (default: weekly).")

    return p


def main():
    """
    Main function that parses command-line arguments, configures and runs the CoordinatorAgent,
    and handles tasks such as emitting a schedule and sending results via email.
    """
    args = build_parser().parse_args()
# ...
# Default from legacy --no-* switches
    enable_sources = {
        "arxiv": not getattr(args, "no_arxiv", False),
        "crossref": not getattr(args, "no_crossref", False),
        "doaj": not getattr(args, "no_doaj", False),
    }

    # If --sources is provided, it overrides the above
    if getattr(args, "sources", None):
        wanted = {s.strip().lower() for s in args.sources.split(",") if s.strip()}
        valid = {"arxiv", "crossref", "doaj"}
        unknown = wanted - valid
        if unknown:
            print(f"⚠ Ignoring unknown sources: {', '.join(sorted(unknown))}")
        enable_sources = {k: (k in wanted) for k in ("arxiv", "crossref", "doaj")}


    # timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    # out_root = Path(args.out).expanduser().resolve()
    # run_dir = out_root / f"run_{timestamp}"
    # run_dir.mkdir(parents=True, exist_ok=True)

    # Coordinator drives the full pipeline
    coordinator = CoordinatorAgent(
        contact_email=args.email,
        timeout=args.timeout,
        enable_sources=enable_sources,
        run_root=Path(args.out).expanduser().resolve(),
    )
    results = coordinator.run(
        query=args.query,
        per_source_limit=args.limit,
        from_year=args.from_year,
        to_year=args.to_year,
    )

    # --- Emit schedule template (optional) ---
    if args.emit_schedule:
        from pathlib import Path as _P
        # Find current run dir from an artefact path
        any_art = results.get("json") or results.get("csv") or results.get("sqlite")
        run_dir = _P(any_art).parent if any_art else _P(args.out)
        sched_path = run_dir / "SCHEDULE.txt"

        # reconstruct the base command (quote query)
        q = args.query.replace('"', '\\"')
        base_cmd = f'python -m aro_agent.cli --query "{q}" --limit {args.limit}'
        # include sources if you used --sources
        try:
            if args.sources:
                base_cmd += f" --sources {args.sources}"
        except AttributeError:
            pass
        if args.from_year is not None:
            base_cmd += f" --from-year {args.from_year}"
        if args.to_year is not None:
            base_cmd += f" --to-year {args.to_year}"
        base_cmd += f' --out "{_P(args.out).resolve()}"'

        # Windows schtasks (weekly @ 09:00 by default)
        sch = (
            'REM ---- Windows Task Scheduler ----\n'
            f'schtasks /Create /SC {"WEEKLY" if args.schedule=="weekly" else "DAILY"} '
            '/TN "ARO-Agent - {query}" /TR "{cmd}" /ST 09:00 /RL LIMITED\n'
        ).format(query=q, cmd=base_cmd)

        # *nix cron (weekly: Monday 09:00; daily: 09:00)
        cron_time = "0 9 * * 1" if args.schedule == "weekly" else "0 9 * * *"
        cron = (
            '### ---- cron (Linux/macOS) ----\n'
            "# Add this line to your crontab (crontab -e):\n"
            f'{cron_time} cd "{_P(args.out).resolve()}" && {base_cmd} >> aro_agent.log 2>&1\n'
        )

        with sched_path.open("w", encoding="utf-8") as f:
            f.write(sch + "\n" + cron)

        print(f"🗓  Wrote schedule template: {sched_path}")


    artefacts = results  # name clarity

    if args.mail_to and args.mail_from:
        to_list = [x.strip() for x in args.mail_to.split(",") if x.strip()]
        resp = build_and_send_email(
            query=args.query,
            artefacts=artefacts,
            sender=args.mail_from,
            recipients=to_list,
            credentials_path=args.gmail_creds,
            token_path=args.gmail_token,
            attach_zip=not args.no_attach,
        )
        print(f"📧 Email sent. Gmail message id: {resp.get('id')}")
    else:
        if args.mail_to or args.mail_from:
            print("⚠ To send email, provide both --mail-to and --mail-from")

    # Save via StorageAgent (already called internally) returns paths

    run_dir = Path(results.get("csv") or results.get("json") or args.out).parent
    print(f"✅ Finished. Saved artefacts in: {run_dir}")

if __name__ == "__main__":
    main()
