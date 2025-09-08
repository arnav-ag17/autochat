from __future__ import annotations

import os
import fnmatch
from pathlib import Path
from typing import Dict, Generator, Iterable, Optional, Tuple


IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".next",
    "build",
    "dist",
    ".DS_Store",
}

INCLUDE_PATTERNS = [
    "*.py",
    "*.js",
    "*.ts",
    "*.tsx",
    "*.jsx",
    "*.json",
    "*.toml",
    "*.yml",
    "*.yaml",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "poetry.lock",
    "package.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Procfile",
    ".env",
    ".env.example",
    ".env.sample",
    "README*",
    "*.md",
    "*.txt",
]


def _should_include(path: Path, patterns: Optional[Iterable[str]]) -> bool:
    if patterns is None:
        patterns = INCLUDE_PATTERNS
    name = path.name
    for pat in patterns:
        if fnmatch.fnmatch(name, pat):
            return True
    return False


def iter_files(root: str | Path, patterns: Optional[Iterable[str]] = None) -> Generator[Tuple[Path, Path], None, None]:
    root_path = Path(root).resolve()
    for dirpath, dirnames, filenames in os.walk(root_path):
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            p = Path(dirpath) / filename
            if _should_include(p, patterns):
                yield p, p.relative_to(root_path)


def read_text(path: str | Path, limit_bytes: int = 1_000_000) -> str:
    p = Path(path)
    try:
        if p.stat().st_size > limit_bytes:
            return ""  # too large, skip content
    except OSError:
        return ""

    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(p, "r", encoding=enc, errors="ignore") as f:
                return f.read()
        except Exception:
            continue
    return ""


def exists_any(root: str | Path, names: list[str]) -> Dict[str, bool]:
    root_path = Path(root)
    return {name: (root_path / name).exists() for name in names}


def glob_first(root: str | Path, patterns: list[str]) -> Optional[str]:
    root_path = Path(root)
    for pat in patterns:
        matches = list(root_path.rglob(pat))
        if matches:
            return str(matches[0])
    return None
