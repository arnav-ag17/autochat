from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .walk import read_text


def detect_static(app_root: str) -> Dict:
    res: Dict = {
        "runtime": None,
        "framework": None,
        "needs_build": False,
        "build_command": None,
        "static_assets": None,
        "app_path": app_root,
        "rationale": [],
    }

    root = Path(app_root)
    # Very simple: if we find build/dist/out with index.html and no server hints,
    for candidate in ("build", "dist", "out"):
        p = root / candidate / "index.html"
        if p.exists():
            res["runtime"] = "static"
            res["framework"] = None
            res["needs_build"] = False
            res["static_assets"] = str(p.parent)
            res["rationale"].append(f"Found static assets at {p.parent}")
            return res

    return res
