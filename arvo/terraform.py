"""
Terraform wrapper functions for deployment orchestration.
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Generator, Tuple

from .state import get_deployment_dir
from .events import emit_event, EventTypes


def _run_terraform_command(
    deployment_id: str, 
    command: list[str], 
    event_type: str,
    success_data: Dict[str, Any] = None
) -> Tuple[bool, str]:
    """
    Run a terraform command and emit events.
    
    Args:
        deployment_id: Deployment ID
        command: Terraform command to run
        event_type: Event type to emit on success
        success_data: Additional data for success event
        
    Returns:
        Tuple of (success, output)
    """
    deployment_dir = get_deployment_dir(deployment_id)
    terraform_log = deployment_dir / "terraform.log"
    
    # Copy terraform files to deployment directory
    _copy_terraform_files(deployment_dir)
    
    try:
        # Run terraform command
        process = subprocess.Popen(
            command,
            cwd=deployment_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        output_lines = []
        with open(terraform_log, "a") as log_file:
            log_file.write(f"=== {' '.join(command)} ===\n")
            
            for line in process.stdout:
                line = line.rstrip()
                output_lines.append(line)
                log_file.write(line + "\n")
                log_file.flush()
                
                # Emit line events for apply command
                if "apply" in command and line.strip():
                    emit_event(deployment_id, EventTypes.TF_APPLY_LINE, {"line": line})
        
        process.wait()
        output = "\n".join(output_lines)
        
        if process.returncode == 0:
            # Success
            data = success_data or {}
            emit_event(deployment_id, event_type, data)
            return True, output
        else:
            # Failure
            error_lines = output_lines[-40:] if len(output_lines) > 40 else output_lines
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": f"Terraform command failed: {' '.join(command)}",
                "hint": "Check terraform.log for details",
                "last_lines": error_lines
            })
            return False, output
            
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Failed to run terraform command: {str(e)}",
            "hint": "Check terraform installation and permissions"
        })
        return False, str(e)


def _copy_terraform_files(deployment_dir: Path) -> None:
    """
    Copy terraform files to deployment directory.
    
    Args:
        deployment_dir: Deployment directory
    """
    # Find terraform files in current directory
    terraform_files = ["main.tf", "variables.tf", "outputs.tf", "bootstrap.sh"]
    
    for file_name in terraform_files:
        src_file = Path(file_name)
        if src_file.exists():
            dst_file = deployment_dir / file_name
            shutil.copy2(src_file, dst_file)
    
    # Copy the infra directory if it exists
    infra_dir = Path("infra")
    if infra_dir.exists():
        dst_infra = deployment_dir / "infra"
        if dst_infra.exists():
            shutil.rmtree(dst_infra)
        shutil.copytree(infra_dir, dst_infra)


def _write_tfvars(deployment_id: str, tfvars: Dict[str, Any]) -> None:
    """
    Write terraform.tfvars.json file.
    
    Args:
        deployment_id: Deployment ID
        tfvars: Terraform variables to write
    """
    deployment_dir = get_deployment_dir(deployment_id)
    tfvars_file = deployment_dir / "terraform.tfvars.json"
    
    with open(tfvars_file, 'w') as f:
        json.dump(tfvars, f, indent=2)


def tf_init(deployment_id: str) -> bool:
    """
    Run terraform init.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        True if successful
    """
    success, _ = _run_terraform_command(
        deployment_id,
        ["terraform", "init", "-upgrade", "-no-color"],
        EventTypes.TF_INIT,
        {"ok": True}
    )
    return success


def tf_plan(deployment_id: str) -> bool:
    """
    Run terraform plan.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        True if successful
    """
    success, output = _run_terraform_command(
        deployment_id,
        ["terraform", "plan", "-no-color"],
        EventTypes.TF_PLAN
    )
    
    if success:
        # Parse plan output for resource counts
        adds = output.count("will be created")
        changes = output.count("will be updated")
        destroys = output.count("will be destroyed")
        
        emit_event(deployment_id, EventTypes.TF_PLAN, {
            "adds": adds,
            "changes": changes,
            "destroys": destroys,
            "ok": True
        })
    
    return success


def tf_apply(deployment_id: str, tf_vars: Dict[str, Any] = None) -> bool:
    """
    Run terraform apply.
    
    Args:
        deployment_id: Deployment ID
        tf_vars: Terraform variables to write
        
    Returns:
        True if successful
    """
    emit_event(deployment_id, EventTypes.TF_APPLY_START, {})
    
    # Write terraform variables to terraform.tfvars.json if provided
    if tf_vars:
        _write_tfvars(deployment_id, tf_vars)
    
    success, output = _run_terraform_command(
        deployment_id,
        ["terraform", "apply", "-auto-approve", "-no-color"],
        EventTypes.TF_APPLY_DONE,
        {"ok": True}
    )
    
    return success


def tf_destroy(deployment_id: str) -> bool:
    """
    Run terraform destroy.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        True if successful
    """
    emit_event(deployment_id, EventTypes.DESTROY_START, {})
    
    success, _ = _run_terraform_command(
        deployment_id,
        ["terraform", "destroy", "-auto-approve", "-no-color"],
        EventTypes.DESTROY_DONE,
        {"ok": True}
    )
    
    return success


def get_terraform_outputs(deployment_id: str) -> Dict[str, Any]:
    """
    Get terraform outputs as JSON.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Dictionary of terraform outputs
    """
    deployment_dir = get_deployment_dir(deployment_id)
    
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=deployment_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        import json
        return json.loads(result.stdout)
        
    except subprocess.CalledProcessError as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Failed to get terraform outputs: {e.stderr}",
            "hint": "Terraform apply may have failed"
        })
        return {}
    except json.JSONDecodeError as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Failed to parse terraform outputs: {str(e)}",
            "hint": "Terraform output format may be unexpected"
        })
        return {}


def get_terraform_output(deployment_id: str, output_name: str) -> str:
    """
    Get a specific terraform output value.
    
    Args:
        deployment_id: Deployment ID
        output_name: Name of the output
        
    Returns:
        Output value as string
    """
    deployment_dir = get_deployment_dir(deployment_id)
    
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=deployment_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Failed to get terraform output '{output_name}': {e.stderr}",
            "hint": "Output may not exist or terraform apply may have failed"
        })
        return ""
