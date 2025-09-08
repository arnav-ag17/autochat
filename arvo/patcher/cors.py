from __future__ import annotations
from typing import Tuple, List

def decide_cors(multi_service: bool) -> Tuple[str, List[str]]:
    if multi_service:
        return "auto", ["multi-service detected; enabling auto CORS if present"]
    return "none", []
