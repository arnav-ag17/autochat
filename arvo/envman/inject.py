from __future__ import annotations

from typing import Dict, Tuple
from .plan import InjectPlan


def make_ec2_snippet(region: str, deployment_id: str, envfile_path: str) -> str:
    return f"""
# Fetch secrets from SSM and write env file
PARAMS=$(aws ssm get-parameters-by-path --with-decryption --region {region} --path "/arvo/{deployment_id}/env/" --query 'Parameters[*].[Name,Value]' --output text)
mkdir -p $(dirname {envfile_path})
: > {envfile_path}
while read -r NAME VALUE; do
  KEY=$(basename "$NAME")
  echo "$KEY=$VALUE" >> {envfile_path}
done <<< "$PARAMS"
chmod 600 {envfile_path}
""".strip()


def plan_injection(target: str, region: str, deployment_id: str, values_plain: Dict[str, str], ssm_paths: Dict[str, str]) -> InjectPlan:
    if target == "static":
        return InjectPlan(target=target, ec2_bootstrap_snippet=None, envfile_path=None, ecs_env={}, ecs_ssm={}, redactions=list(ssm_paths.keys()))

    if target == "ec2":
        envfile = "/etc/default/arvo-app"
        snippet = make_ec2_snippet(region, deployment_id, envfile)
        return InjectPlan(target=target, ec2_bootstrap_snippet=snippet, envfile_path=envfile, ecs_env={}, ecs_ssm={}, redactions=list(ssm_paths.keys()))

    # ecs/lightsail
    ecs_env = dict(values_plain)
    ecs_ssm = dict(ssm_paths)
    return InjectPlan(target=target, ec2_bootstrap_snippet=None, envfile_path=None, ecs_env=ecs_env, ecs_ssm=ecs_ssm, redactions=list(ssm_paths.keys()))
