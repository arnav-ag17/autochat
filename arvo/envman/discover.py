from __future__ import annotations

import re
from pathlib import Path
from typing import List, Set
from arvo.analyzer.spec import DeploymentSpec

ENV_FILE_NAMES = [".env", ".env.example", ".env.sample"]
PY_PATTERNS = [r"os\.environ\[['\"]([A-Z0-9_]+)['\"]\]", r"os\.getenv\(['\"]([A-Z0-9_]+)['\"]\)"]
JS_PATTERNS = [r"process\.env\.([A-Z0-9_]+)"]
SAFE_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".env", ".txt", ".md"}


def parse_envfile_keys(path: Path) -> List[str]:
    keys: List[str] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k = line.split("=", 1)[0].strip()
            if k:
                keys.append(k)
    except Exception:
        pass
    return keys


def discover_required_keys(spec: DeploymentSpec, workspace: str) -> List[str]:
    req: List[str] = []
    seen: Set[str] = set()

    # from spec
    for k in spec.env_required:
        if k not in seen:
            seen.add(k)
            req.append(k)

    ws = Path(workspace)
    # from env files
    for name in ENV_FILE_NAMES:
        p = ws / name
        if p.exists():
            for k in parse_envfile_keys(p):
                if k not in seen:
                    seen.add(k)
                    req.append(k)

    # lightweight code scans
    py_regex = re.compile("|".join(PY_PATTERNS))
    js_regex = re.compile("|".join(JS_PATTERNS))

    for f in ws.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in SAFE_EXT:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in py_regex.findall(text):
            k = m if isinstance(m, str) else next((x for x in m if x), None)
            if k and k not in seen:
                seen.add(k)
                req.append(k)
        for m in js_regex.findall(text):
            k = m if isinstance(m, str) else next((x for x in m if x), None)
            if k and k not in seen:
                seen.add(k)
                req.append(k)

    return req
