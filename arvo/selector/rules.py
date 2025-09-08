from typing import Dict, List, Tuple
from arvo.analyzer.spec import DeploymentSpec

SUPPORTED_TARGETS = {"ec2", "ecs_fargate", "s3_cf", "lightsail_containers", "lambda"}


def apply_overrides(spec: DeploymentSpec, overrides: Dict | None) -> Tuple[str | None, Dict, List[str], List[str], bool]:
    if not overrides:
        return None, {}, [], [], False
    rationale: List[str] = []
    warnings: List[str] = []
    fallback_used = False

    forced = overrides.get("infra")
    params = {k: v for k, v in (overrides or {}).items() if k != "infra"}

    if forced:
        if forced not in SUPPORTED_TARGETS:
            warnings.append(f"override target '{forced}' not supported; falling back")
            fallback_used = True
            forced = None
        elif forced == "lambda":
            warnings.append("lambda not implemented; falling back to ec2")
            fallback_used = True
            forced = None
        else:
            rationale.append(f"override requested infra={forced}")

    return forced, params, rationale, warnings, fallback_used


def score_spec(spec: DeploymentSpec) -> Tuple[str, Dict, List[str], List[str], float]:
    rationale: List[str] = []
    warnings: List[str] = []
    params: Dict[str, object] = {}
    confidence = 0.5

    # Containerized
    if spec.containerized or "Dockerfile" in spec.manifests or "docker-compose.yml" in spec.manifests:
        target = "ecs_fargate"
        params["port"] = spec.port or 8080
        params["needs_build"] = True
        params["image_source"] = "dockerfile"
        rationale.append("container signals: containerized or Dockerfile/Compose present")
        confidence = min(1.0, confidence + 0.2)
        if spec.multi_service:
            warnings.append("multi-service repo detected; deploying likely web service only in v1")
        if spec.db_required:
            warnings.append("database required detected; v1 will deploy without managed DB")
        return target, params, rationale, warnings, confidence

    # Static
    if spec.runtime == "static" and spec.static_assets:
        target = "s3_cf"
        params["static_assets"] = spec.static_assets
        params["needs_build"] = bool(spec.needs_build)
        rationale.append("static assets detected; no backend server")
        confidence = min(1.0, confidence + 0.2)
        return target, params, rationale, warnings, confidence

    # Default EC2
    target = "ec2"
    params["port"] = spec.port or 8080
    params["start_command"] = spec.start_command
    params["needs_build"] = bool(spec.needs_build)
    if spec.framework:
        rationale.append(f"runtime={spec.runtime} framework={spec.framework}")
        confidence = min(1.0, confidence + 0.2)
    else:
        rationale.append(f"non-containerized web app; defaulting to EC2 ({spec.runtime})")
    if spec.multi_service:
        warnings.append("multi-service repo detected; deploying backend only in v1")
    if spec.db_required:
        warnings.append("database required detected; v1 will deploy without managed DB")
    return target, params, rationale, warnings, confidence
