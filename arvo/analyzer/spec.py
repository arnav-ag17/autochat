from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DeploymentSpec:
    # Core identity
    app_path: str
    runtime: str
    framework: Optional[str]
    containerized: bool
    multi_service: bool

    # Execution
    start_command: Optional[str]
    port: Optional[int]
    health_path: str
    needs_build: bool
    build_command: Optional[str]
    static_assets: Optional[str]
    db_required: bool

    # Inputs & config
    env_required: List[str]
    env_example_path: Optional[str]

    # Risk & rewrites
    localhost_refs: List[str]
    loopback_binds: List[str]
    warnings: List[str]
    rationale: List[str]

    # Raw manifests for later stages (paths)
    manifests: Dict[str, str]

    # Free-form extras per runtime
    extra: Dict[str, str] = field(default_factory=dict)
