from __future__ import annotations

from typing import Dict, List, Tuple
import os

NON_SENSITIVE = {"PORT", "ENV", "DEBUG", "NODE_ENV", "PYTHONUNBUFFERED"}


def classify_values(required_keys: List[str], overrides_env: Dict[str, str] | None, parsed_env: Dict[str, str] | None, noninteractive: bool) -> Tuple[Dict[str, str], Dict[str, str], List[str], List[str]]:
    values_plain: Dict[str, str] = {}
    values_secret: Dict[str, str] = {}
    missing: List[str] = []
    provided: List[str] = []

    merged: Dict[str, str] = {}
    for source in (parsed_env or {}, overrides_env or {}):
        for k, v in source.items():
            merged[k] = v

    for k in required_keys:
        if k in merged and merged[k] is not None:
            provided.append(k)
            if k in NON_SENSITIVE:
                values_plain[k] = merged[k]
            else:
                values_secret[k] = merged[k]
        else:
            missing.append(k)

    # Non-interactive: keep missing as warnings; no prompt in v1
    return values_plain, values_secret, missing, provided
