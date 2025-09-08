from __future__ import annotations

import json
import subprocess
from typing import Dict, Tuple


def ssm_path(deployment_id: str, key: str) -> str:
    return f"/arvo/{deployment_id}/env/{key}"


def put_parameters(region: str, deployment_id: str, values_secret: Dict[str, str]) -> Dict[str, str]:
    paths: Dict[str, str] = {}
    for k, v in values_secret.items():
        path = ssm_path(deployment_id, k)
        cmd = [
            "aws", "ssm", "put-parameter",
            "--region", region,
            "--name", path,
            "--type", "SecureString",
            "--overwrite",
            "--value", v,
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        paths[k] = path
    return paths


def delete_parameters(region: str, deployment_id: str) -> int:
    # get by path, then delete in batches
    get_cmd = [
        "aws", "ssm", "get-parameters-by-path",
        "--region", region,
        "--path", f"/arvo/{deployment_id}/env/",
        "--with-decryption",
    ]
    proc = subprocess.run(get_cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        return 0
    data = json.loads(proc.stdout or "{}")
    names = [p["Name"] for p in data.get("Parameters", [])]
    if not names:
        return 0
    del_cmd = [
        "aws", "ssm", "delete-parameters",
        "--region", region,
        "--names",
        *names,
    ]
    subprocess.run(del_cmd, check=False, capture_output=True, text=True)
    return len(names)
