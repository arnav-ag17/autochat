from __future__ import annotations

import re
from typing import Dict

TOKENISH = re.compile(r"(?i)(secret|token|password|apikey|api_key)")
HEX_LONG = re.compile(r"\b[0-9a-f]{32,}\b", re.I)


def redact_string(s: str) -> str:
    if TOKENISH.search(s) or HEX_LONG.search(s):
        return "[REDACTED]"
    return s


def redact_dict(d: Dict[str, str]) -> Dict[str, str]:
    return {k: "[REDACTED]" for k in d.keys()}
