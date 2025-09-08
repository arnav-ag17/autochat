from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple, Optional

MARK = "ARVO_PATCH"

SAFE_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".html", ".env", ".toml", ".cfg", ".ini"}

LOCALHOST_URL = re.compile(r"http://(localhost|127\.0\.0\.1):\d+/?")


def is_safe_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in SAFE_EXT:
        try:
            return path.stat().st_size < 1_000_000
        except OSError:
            return False
    return False


def replace_localhost_with_relative(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []
    orig = text
    text = LOCALHOST_URL.sub("/", text)
    if text != orig:
        changes.append(f"{MARK}: api_base=relative")
    return text, changes


def replace_localhost_with_origin(text: str, placeholder: str) -> Tuple[str, List[str]]:
    changes: List[str] = []
    orig = text
    text = LOCALHOST_URL.sub(f"{placeholder}/", text)
    if text != orig:
        changes.append(f"{MARK}: api_base=service_origin")
    return text, changes


def replace_loopback_binds(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []
    new = re.sub(r"(['\"])(127\.0\.0\.1|localhost)(['\"])", r"'0.0.0.0'", text)
    if new != text:
        changes.append(f"{MARK}: bind=0.0.0.0")
    return new, changes


def ensure_env_port(text: str, default_port: int) -> Tuple[str, List[str]]:
    changes: List[str] = []
    # Python: app.run(port=5000) → env default
    py_new = re.sub(r"port\s*=\s*(\d+)", f"port=int(os.getenv('PORT',{default_port}))", text)
    if py_new != text:
        return py_new, [f"{MARK}: python_port_env"]
    # Node: listen(3000) → process.env.PORT || 3000
    js_new = re.sub(r"listen\((\d+)\)", r"listen(process.env.PORT || \1)", text)
    if js_new != text:
        return js_new, [f"{MARK}: node_port_env"]
    return text, changes


def rewrite_file(path: Path, default_port: int, service_origin: Optional[str] = None, force_origin: bool = False) -> List[str]:
    if not is_safe_file(path):
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    if MARK in content:
        return []  # already patched

    changed = False
    changes: List[str] = []

    if force_origin and service_origin:
        new, ch = replace_localhost_with_origin(content, "${SERVICE_ORIGIN}")
    else:
        new, ch = replace_localhost_with_relative(content)
    if ch:
        content = new
        changes.extend(ch)
        changed = True

    new, ch = replace_loopback_binds(content)
    if ch:
        content = new
        changes.extend(ch)
        changed = True

    new, ch = ensure_env_port(content, default_port)
    if ch:
        content = new
        changes.extend(ch)
        changed = True

    if changed:
        content = content + f"\n# {MARK}\n"
        try:
            path.write_text(content, encoding="utf-8")
        except Exception:
            return []
    return changes
