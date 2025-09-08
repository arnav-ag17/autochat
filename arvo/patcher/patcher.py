from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, List

from arvo.analyzer.spec import DeploymentSpec
from arvo.selector.plan import InfraPlan
from .report import PatchResult
from .rewrites import rewrite_file
from .commands import synthesize_start
from .systemd import generate_systemd_unit
from .container import generate_container_cmd, generate_container_entrypoint
from .cors import decide_cors
from .health import normalize_health_path


def apply_patches(
    spec: DeploymentSpec,
    plan: InfraPlan,
    workspace: str,
    service_origin: Optional[str] = None,
) -> PatchResult:
    ws = Path(workspace).resolve()
    changes: List[str] = []
    warnings: List[str] = []
    rationale: List[str] = []

    # 1) Rewrites over safe files
    default_port = spec.port or 8080
    for p in ws.rglob("*"):
        ch = rewrite_file(p, default_port, service_origin=service_origin, force_origin=spec.multi_service)
        if ch:
            changes.extend([f"{p}: {c}" for c in ch])

    # 2) CORS decision
    cors_mode, cors_notes = decide_cors(spec.multi_service)
    rationale.extend(cors_notes)

    # 3) Health path
    health_path = normalize_health_path(spec.health_path)

    # 4) Start command synthesis
    start_command, start_notes = synthesize_start(spec)
    rationale.extend(start_notes)

    systemd_unit = None
    container_cmd = None
    container_entrypoint = None

    if plan.target == "ec2":
        if start_command:
            systemd_unit = generate_systemd_unit(str(ws), start_command, default_port)
            changes.append("generated systemd unit")
        else:
            warnings.append("no start command for EC2 target")
    elif plan.target in {"ecs_fargate", "lightsail_containers"}:
        if start_command:
            container_cmd, notes = generate_container_cmd(start_command, default_port)
            rationale.extend(notes)
            entry, notes2 = generate_container_entrypoint(start_command)
            container_entrypoint = entry
            rationale.extend(notes2)
        else:
            warnings.append("no start command for container target")

    env_overrides: Dict[str, str] = {"PORT": str(default_port)}

    return PatchResult(
        patched_app_path=str(ws),
        start_command=start_command,
        env_overrides=env_overrides,
        health_path=health_path,
        cors_mode=cors_mode,
        systemd_unit=systemd_unit,
        container_cmd=container_cmd,
        container_entrypoint=container_entrypoint,
        warnings=warnings,
        changes=changes,
        rationale=rationale,
    )
