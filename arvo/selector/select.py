from typing import Dict, Optional
from .plan import InfraPlan
from .rules import apply_overrides, score_spec
from .explain import finalize_rationale
from arvo.analyzer.spec import DeploymentSpec


def select_infra(spec: DeploymentSpec, overrides: Dict | None = None) -> InfraPlan:
    forced_target, override_params, override_rationale, override_warnings, fallback_used = apply_overrides(spec, overrides)

    if forced_target:
        params = {"port": spec.port or 8080, "needs_build": bool(spec.needs_build)}
        if forced_target == "ecs_fargate":
            params.update({"image_source": "dockerfile"})
            module_hint = "ecs_web"
        elif forced_target == "s3_cf":
            params.update({"static_assets": spec.static_assets})
            module_hint = "static_site"
        elif forced_target == "lightsail_containers":
            params.update({"image_source": "dockerfile"})
            module_hint = "lightsail_web"
        elif forced_target == "lambda":
            module_hint = "lambda_api"
        else:
            params.update({"start_command": spec.start_command})
            module_hint = "ec2_web"
        rationale = finalize_rationale(override_rationale + [f"override applied → {forced_target}"])
        return InfraPlan(target=forced_target, module_hint=module_hint, parameters={**params, **override_params},
                         rationale=rationale, warnings=override_warnings, confidence=0.9, fallback_used=fallback_used)

    target, params, rationale, warnings, confidence = score_spec(spec)
    if target == "ecs_fargate":
        module_hint = "ecs_web"
    elif target == "s3_cf":
        module_hint = "static_site"
    elif target == "lightsail_containers":
        module_hint = "lightsail_web"
    elif target == "lambda":
        module_hint = "lambda_api"
    else:
        module_hint = "ec2_web"

    if override_params:
        params.update(override_params)
        rationale.append("overrides passed through to parameters")

    return InfraPlan(target=target, module_hint=module_hint, parameters=params,
                     rationale=finalize_rationale(rationale), warnings=warnings,
                     confidence=confidence, fallback_used=fallback_used)
