from __future__ import annotations

from typing import Dict, Tuple
from arvo.analyzer.spec import DeploymentSpec
from arvo.selector.plan import InfraPlan
from .plan import EnvPlan, InjectPlan
from .discover import discover_required_keys
from .collect import classify_values
from .ssm import put_parameters
from .inject import plan_injection


def prepare_env(
    deployment_id: str,
    region: str,
    spec: DeploymentSpec,
    plan: InfraPlan,
    overrides_env: Dict[str, str] | None,
    noninteractive: bool = True,
    workspace: str | None = None,
) -> tuple[EnvPlan, InjectPlan]:
    ws = workspace or spec.app_path

    req = discover_required_keys(spec, ws)
    values_plain, values_secret, missing, provided = classify_values(req, overrides_env, None, noninteractive)

    ssm_paths = {}
    warnings = []
    if req and plan.target != "static" and values_secret:
        try:
            ssm_paths = put_parameters(region, deployment_id, values_secret)
        except Exception as e:
            # propagate minimal hint
            raise RuntimeError("Failed to store secrets in SSM. Check IAM: ssm:PutParameter") from e
    elif plan.target == "static" and req:
        warnings.append("static target ignores env keys; consider backend separation")

    envplan = EnvPlan(
        required_keys=req,
        provided_keys=provided,
        missing_keys=missing,
        values_plain=values_plain,
        values_secret={k: "[REDACTED]" for k in values_secret},
        ssm_paths=ssm_paths,
        warnings=warnings,
    )

    inject = plan_injection(plan.target, region, deployment_id, values_plain, ssm_paths)
    return envplan, inject
