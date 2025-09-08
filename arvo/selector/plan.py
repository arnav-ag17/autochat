from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class InfraPlan:
    target: str
    module_hint: str
    parameters: Dict[str, object]
    rationale: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 0.5
    fallback_used: bool = False
