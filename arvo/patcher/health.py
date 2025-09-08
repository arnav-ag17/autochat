from __future__ import annotations
from typing import List

def normalize_health_path(spec_health: str | None) -> str:
    if spec_health and len(spec_health) > 0:
        return spec_health
    # default candidates
    return "/health"
