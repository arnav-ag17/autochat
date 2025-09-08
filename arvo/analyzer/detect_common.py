from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .walk import iter_files, read_text, exists_any, glob_first


MANIFEST_NAMES = [
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "poetry.lock",
    "package.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Dockerfile",
    "docker-compose.yml",
    "Procfile",
]

ENV_FILES = [".env", ".env.example", ".env.sample"]

LOCALHOST_PATTERNS = [
    r"http://localhost",
    r"https://localhost",
    r"http://127\.0\.0\.1",
    r"127\.0\.0\.1",
]

HEALTH_HINTS = ["/health", "/healthz", "/ping", "/status"]


def find_manifests(root: str) -> Dict[str, str]:
    root_path = Path(root)
    found: Dict[str, str] = {}
    
    # Check root directory first
    for name in MANIFEST_NAMES:
        p = root_path / name
        if p.exists():
            found[name] = str(p)
    
    # Check common subdirectories for Python/Node manifests
    subdirs = ["app", "src", "application", "web", "backend", "frontend"]
    for subdir in subdirs:
        subdir_path = root_path / subdir
        if subdir_path.exists():
            for name in MANIFEST_NAMES:
                if name not in found:  # Only if not found in root
                    p = subdir_path / name
                    if p.exists():
                        found[name] = str(p)
    
    # also try rglob for package.json if nested
    if "package.json" not in found:
        first_pkg = glob_first(root_path, ["**/package.json"])
        if first_pkg:
            found["package.json"] = first_pkg
    
    return found


def parse_env_requirements(root: str) -> Tuple[List[str], Optional[str]]:
    env_keys: set[str] = set()
    env_example_path: Optional[str] = None

    # Parse .env-like files
    for fname in ENV_FILES:
        p = Path(root) / fname
        if p.exists():
            if env_example_path is None and fname != ".env":
                env_example_path = str(p)
            try:
                for line in read_text(p).splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key = line.split("=", 1)[0].strip()
                        if key:
                            env_keys.add(key)
            except Exception:
                pass

    # Grep code for env usages
    env_regexes = [
        r"os\.environ\[[\'\"]([A-Z0-9_]+)[\'\"]\]",
        r"os\.getenv\([\'\"]([A-Z0-9_]+)[\'\"]\)",
        r"process\.env\.([A-Z0-9_]+)",
    ]
    combined = re.compile("|".join(env_regexes))

    for fp, _ in iter_files(root):
        try:
            text = read_text(fp)
            if not text:
                continue
            for m in combined.finditer(text):
                for i in range(1, m.lastindex + 1 if m.lastindex else 1):
                    val = m.group(i)
                    if val:
                        env_keys.add(val)
        except Exception:
            continue

    return sorted(env_keys), env_example_path


def find_localhost_refs(root: str) -> Tuple[List[str], List[str]]:
    localhost_files: List[str] = []
    loopback_binds: List[str] = []
    bind_regex = re.compile(r"(host|bind)\s*[:=]\s*[\'\"]?127\.0\.0\.1")

    for fp, _ in iter_files(root):
        text = read_text(fp)
        if not text:
            continue
        if any(re.search(pat, text) for pat in LOCALHOST_PATTERNS):
            localhost_files.append(str(fp))
        if bind_regex.search(text):
            loopback_binds.append(str(fp))
    return localhost_files, loopback_binds


def infer_health_path(root: str) -> str:
    for fp, _ in iter_files(root):
        text = read_text(fp)
        if not text:
            continue
        for hp in HEALTH_HINTS:
            if hp in text:
                return hp
    return "/"
