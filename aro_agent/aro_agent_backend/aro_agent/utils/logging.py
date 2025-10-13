from __future__ import annotations
import json, sys
from datetime import datetime
from pathlib import Path

class RunLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "aro_agent.log"

    def _ts(self) -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def info(self, msg: str, **kv):
        line = {"ts": self._ts(), "level": "INFO", "msg": msg, **kv}
        self._write(line)

    def warn(self, msg: str, **kv):
        line = {"ts": self._ts(), "level": "WARN", "msg": msg, **kv}
        self._write(line)

    def error(self, msg: str, **kv):
        line = {"ts": self._ts(), "level": "ERROR", "msg": msg, **kv}
        self._write(line)

    def _write(self, line: dict):
        txt = json.dumps(line, ensure_ascii=False)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(txt + "\n")
        # Also echo important lines to console
        if line["level"] in {"ERROR", "WARN"}:
            print(txt, file=sys.stderr)
