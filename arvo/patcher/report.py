from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PatchResult:
    patched_app_path: str
    start_command: Optional[str]
    env_overrides: Dict[str, str]
    health_path: str
    cors_mode: str
    systemd_unit: Optional[str]
    container_cmd: Optional[List[str]]
    container_entrypoint: Optional[List[str]]
    warnings: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)
    idempotency_marker: str = "arvo_patcher:v1"
