from __future__ import annotations

from typing import Optional, Tuple, List
from arvo.analyzer.spec import DeploymentSpec
from arvo.selector.plan import InfraPlan


def synthesize_start(spec: DeploymentSpec) -> Tuple[Optional[str], List[str]]:
    rationale: List[str] = []
    cmd: Optional[str] = None

    if spec.runtime == "python":
        if spec.framework == "fastapi" and spec.start_command:
            cmd = spec.start_command if "uvicorn" in spec.start_command else None
            if not cmd:
                cmd = "uvicorn main:app"
            rationale.append("uvicorn selected for FastAPI")
        elif spec.framework == "django":
            cmd = "python manage.py runserver"
            rationale.append("Django runserver")
        else:
            cmd = spec.start_command or "flask run"
            rationale.append("Flask run default")
    elif spec.runtime == "node":
        if spec.framework == "nextjs":
            cmd = "npm run start"
            rationale.append("Next.js production start")
        else:
            cmd = spec.start_command or "node server.js"
            rationale.append("Express/Node default")
    elif spec.runtime == "static":
        cmd = None
        rationale.append("Static site - no start command")
    else:
        cmd = spec.start_command
        rationale.append("Unknown runtime - pass through")

    return cmd, rationale
