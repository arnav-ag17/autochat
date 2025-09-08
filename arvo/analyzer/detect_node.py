from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional

from .walk import read_text


def _read_package_json(root: Path) -> Optional[dict]:
    pj = root / "package.json"
    if not pj.exists():
        return None
    try:
        return json.loads(read_text(pj) or "{}")
    except Exception:
        return None


def detect_node(app_root: str) -> Dict:
    res: Dict = {
        "runtime": None,
        "framework": None,
        "start_command": None,
        "port": None,
        "needs_build": False,
        "build_command": None,
        "static_assets": None,
        "db_required": False,
        "containerized": False,
        "app_path": app_root,
        "rationale": [],
    }

    root = Path(app_root)
    pkg = _read_package_json(root)
    if not pkg:
        return res

    res["runtime"] = "node"

    deps = {**(pkg.get("dependencies", {}) or {}), **(pkg.get("devDependencies", {}) or {})}
    scripts = pkg.get("scripts", {}) or {}

    def has_dep(name: str) -> bool:
        return name in deps

    # Framework detection
    if has_dep("next"):
        res["framework"] = "nextjs"
        res["needs_build"] = True
        res["build_command"] = scripts.get("build", "npm run build")
        res["start_command"] = scripts.get("start", "next start")
        res["port"] = 3000
        res["rationale"].append("Detected Next.js via dependency 'next'")
    elif has_dep("express") or re.search(r"(require\(['\"]express['\"]\)|from\s+express\s+import|import\s+express)", json.dumps(pkg)):
        res["framework"] = "express"
        res["start_command"] = scripts.get("start") or ("node server.js" if (root / "server.js").exists() else "node index.js")
        res["port"] = 3000
        res["rationale"].append("Detected Express via dependency or code hint")
    elif has_dep("react") and ("build" in scripts):
        res["framework"] = "react"
        res["needs_build"] = True
        res["build_command"] = scripts.get("build", "npm run build")
        # static site output
        for candidate in ("build", "dist", "out"):
            if (root / candidate / "index.html").exists():
                res["static_assets"] = str(root / candidate)
                break
        res["port"] = None
        res["rationale"].append("Detected React static build via scripts and deps")

    # containerized if Dockerfile exists here
    if (root / "Dockerfile").exists():
        res["containerized"] = True

    # DB heuristic
    if any(dep in deps for dep in ["pg", "pg-promise", "mysql2", "mongoose", "prisma", "redis"]):
        res["db_required"] = True

    return res
