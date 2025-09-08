from __future__ import annotations

from typing import Optional
from .spec import DeploymentSpec
from .heuristics import resolve_spec
from .fetcher import fetch_into_workspace


def analyze_repo(app_root: str, instructions: str = "") -> DeploymentSpec:
    """
    Perform static analysis on app_root and return a DeploymentSpec.
    Must never execute user code. File-size and count limits apply.
    """
    # instructions are not yet used for heuristics but can be appended to rationale later
    spec = resolve_spec(app_root)
    if instructions:
        spec.rationale.append("Instructions provided by user were recorded for context.")
    return spec
