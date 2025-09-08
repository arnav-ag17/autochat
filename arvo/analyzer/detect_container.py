from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict

from .walk import read_text


def detect_container(app_root: str) -> Dict:
    res: Dict = {
        "containerized": False,
        "runtime": None,
        "multi_service": False,
        "app_path": app_root,
        "rationale": [],
    }

    root = Path(app_root)
    dockerfile = root / "Dockerfile"
    compose = root / "docker-compose.yml"

    if dockerfile.exists():
        res["containerized"] = True
        res["runtime"] = "container"
        # Enrich runtime hint from base image
        df_text = read_text(dockerfile)
        if "FROM python" in df_text:
            res["rationale"].append("Dockerfile base is python")
        if "FROM node" in df_text:
            res["rationale"].append("Dockerfile base is node")

    if compose.exists():
        res["containerized"] = True
        res["runtime"] = res["runtime"] or "container"
        try:
            data = yaml.safe_load(read_text(compose) or "{}") or {}
            services = data.get("services", {})
            if isinstance(services, dict) and len(services) > 1:
                res["multi_service"] = True
                # naive selection: prefer service exposing typical web ports
                preferred = None
                for name, svc in services.items():
                    ports = svc.get("ports", []) if isinstance(svc, dict) else []
                    for p in ports:
                        if any(x in str(p) for x in ("80", "8080", "3000", "5000", "8000")):
                            preferred = name
                            break
                    if preferred:
                        break
                if preferred:
                    res["rationale"].append(f"compose multi-service; primary likely '{preferred}'")
        except Exception:
            pass

    return res
