from __future__ import annotations

import json
from pathlib import Path
from .spec import DeploymentSpec


def emit_report(spec: DeploymentSpec, dest_path: str) -> None:
    dest = Path(dest_path)
    dest.mkdir(parents=True, exist_ok=True)
    # JSON spec
    with open(dest / "deployment_spec.json", "w") as f:
        json.dump(spec.__dict__, f, indent=2)
    # Human summary
    lines = []
    lines.append(f"Runtime: {spec.runtime}")
    lines.append(f"Framework: {spec.framework}")
    lines.append(f"App path: {spec.app_path}")
    lines.append(f"Start command: {spec.start_command}")
    lines.append(f"Port: {spec.port}")
    lines.append(f"Health path: {spec.health_path}")
    lines.append(f"Needs build: {spec.needs_build}")
    lines.append(f"Build command: {spec.build_command}")
    lines.append(f"Static assets: {spec.static_assets}")
    lines.append(f"Containerized: {spec.containerized}")
    lines.append(f"Multi-service: {spec.multi_service}")
    lines.append(f"DB required: {spec.db_required}")
    lines.append("")
    if spec.warnings:
        lines.append("Warnings:")
        for w in spec.warnings:
            lines.append(f"- {w}")
        lines.append("")
    if spec.rationale:
        lines.append("Rationale:")
        for r in spec.rationale:
            lines.append(f"- {r}")
        lines.append("")
    lines.append("Manifests:")
    for k, v in spec.manifests.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("Environment keys (required):")
    for k in spec.env_required:
        lines.append(f"- {k}")

    with open(dest / "analysis.md", "w") as f:
        f.write("\n".join(lines))
