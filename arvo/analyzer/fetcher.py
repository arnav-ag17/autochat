from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Tuple

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

MAX_FILES = 50_000
MAX_TOTAL_BYTES = 200 * 1024 * 1024  # 200 MB


def _safe_copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    total_files = 0
    total_bytes = 0

    for root, dirs, files in os.walk(src):
        # prune
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        rel = Path(root).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)

        for f in files:
            if f in IGNORE_DIRS:
                continue
            sp = Path(root) / f
            dp = dst / rel / f
            try:
                size = sp.stat().st_size
            except OSError:
                continue

            total_files += 1
            total_bytes += size
            if total_files > MAX_FILES or total_bytes > MAX_TOTAL_BYTES:
                # stop copying further
                return

            try:
                shutil.copy2(sp, dp)
            except Exception:
                continue


def _hash_file(path: Path, limit_bytes: int = 10 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
    except Exception:
        pass
    return h.hexdigest()[:12]


def fetch_into_workspace(source: str, workspace_root: str) -> Tuple[str, str]:
    """
    Returns (checkout_path, commit_hint).
    - If git: shallow clone to workspace; commit_hint = commit SHA (or 'HEAD').
    - If zip: download, unzip to workspace; commit_hint = file hash prefix.
    - If local: copy tree (rsync-like) into workspace; commit_hint = "local".
    Should ignore: .git, node_modules, .venv, __pycache__, dist/build artifacts.
    """
    workspace = Path(workspace_root).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    # Git URL
    if source.startswith("http://") or source.startswith("https://"):
        if source.endswith(".zip"):
            # ZIP download
            zip_path = workspace / "repo.zip"
            urllib.request.urlretrieve(source, zip_path)
            commit_hint = _hash_file(zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(workspace / "checkout")
            checkout = workspace / "checkout"
            # if a single top dir, use it
            entries = [p for p in checkout.iterdir() if p.is_dir()]
            if len(entries) == 1:
                return str(entries[0].resolve()), commit_hint
            return str(checkout.resolve()), commit_hint
        else:
            # assume public git HTTPS
            checkout = workspace / "checkout"
            try:
                subprocess.run([
                    "git", "clone", "--depth", "1", "--no-single-branch", source, str(checkout)
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"git clone failed: {e.stderr.decode(errors='ignore')}")
            # get HEAD sha if possible
            sha = "HEAD"
            try:
                r = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
                sha = r.stdout.strip()[:12]
            except Exception:
                pass
            return str(checkout.resolve()), sha

    # Local path
    src_path = Path(source).expanduser().resolve()
    if src_path.exists():
        checkout = workspace / "checkout"
        _safe_copy_tree(src_path, checkout)
        return str(checkout.resolve()), "local"

    raise ValueError(f"Unsupported source: {source}")
