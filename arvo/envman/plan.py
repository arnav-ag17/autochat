from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnvPlan:
    required_keys: List[str]
    provided_keys: List[str]
    missing_keys: List[str]
    values_plain: Dict[str, str]
    values_secret: Dict[str, str]
    ssm_paths: Dict[str, str]
    warnings: List[str] = field(default_factory=list)


@dataclass
class InjectPlan:
    target: str
    ec2_bootstrap_snippet: Optional[str]
    envfile_path: Optional[str]
    ecs_env: Dict[str, str]
    ecs_ssm: Dict[str, str]
    redactions: List[str] = field(default_factory=list)
