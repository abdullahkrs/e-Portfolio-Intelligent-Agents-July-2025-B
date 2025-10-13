from __future__ import annotations
import os, zipfile
from pathlib import Path
from typing import Iterable

def make_zip(paths: Iterable[str], out_path: str) -> str:
    """Compresses files into one zip archive and returns the zip path."""
    p_out = Path(out_path)
    p_out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in paths:
            if f and os.path.exists(f):
                zf.write(f, arcname=os.path.basename(f))
    return str(p_out)
