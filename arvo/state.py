"""
State management for deployments.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .ids import is_valid_deployment_id


def get_arvo_home() -> Path:
    """
    Get the Arvo home directory.
    
    Returns:
        Path: Arvo home directory
    """
    arvo_home = os.environ.get("ARVO_HOME", ".arvo")
    return Path(arvo_home).resolve()


def get_deployment_dir(deployment_id: str) -> Path:
    """
    Get the directory for a specific deployment.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Path: Deployment directory
        
    Raises:
        ValueError: If deployment ID is invalid
    """
    if not is_valid_deployment_id(deployment_id):
        raise ValueError(f"Invalid deployment ID: {deployment_id}")
    
    return get_arvo_home() / deployment_id


def create_deployment_dir(deployment_id: str) -> Path:
    """
    Create deployment directory and return its path.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Path: Created deployment directory
    """
    deployment_dir = get_deployment_dir(deployment_id)
    deployment_dir.mkdir(parents=True, exist_ok=True)
    return deployment_dir


def write_env_json(deployment_id: str, instructions: str, repo: str, region: str = "us-west-2") -> None:
    """
    Write environment configuration to env.json.
    
    Args:
        deployment_id: Deployment ID
        instructions: Deployment instructions
        repo: Repository URL
        region: AWS region
    """
    deployment_dir = get_deployment_dir(deployment_id)
    env_data = {
        "instructions": instructions,
        "repo": repo,
        "region": region,
        "created_at": datetime.now().isoformat()
    }
    
    with open(deployment_dir / "env.json", "w") as f:
        json.dump(env_data, f, indent=2)


def read_env_json(deployment_id: str) -> Dict[str, Any]:
    """
    Read environment configuration from env.json.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Dict: Environment configuration
        
    Raises:
        FileNotFoundError: If env.json doesn't exist
    """
    deployment_dir = get_deployment_dir(deployment_id)
    env_file = deployment_dir / "env.json"
    
    if not env_file.exists():
        raise FileNotFoundError(f"Deployment {deployment_id} not found")
    
    with open(env_file, "r") as f:
        return json.load(f)


def write_outputs_json(deployment_id: str, outputs: Dict[str, Any]) -> None:
    """
    Write Terraform outputs to outputs.json.
    
    Args:
        deployment_id: Deployment ID
        outputs: Terraform outputs
    """
    deployment_dir = get_deployment_dir(deployment_id)
    
    with open(deployment_dir / "outputs.json", "w") as f:
        json.dump(outputs, f, indent=2)


def read_outputs_json(deployment_id: str) -> Optional[Dict[str, Any]]:
    """
    Read Terraform outputs from outputs.json.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Dict: Terraform outputs or None if not found
    """
    deployment_dir = get_deployment_dir(deployment_id)
    outputs_file = deployment_dir / "outputs.json"
    
    if not outputs_file.exists():
        return None
    
    with open(outputs_file, "r") as f:
        return json.load(f)


def list_deployments() -> list[str]:
    """
    List all deployment IDs.
    
    Returns:
        List of deployment IDs
    """
    arvo_home = get_arvo_home()
    
    if not arvo_home.exists():
        return []
    
    deployments = []
    for item in arvo_home.iterdir():
        if item.is_dir() and is_valid_deployment_id(item.name):
            deployments.append(item.name)
    
    return sorted(deployments, reverse=True)  # Most recent first


def deployment_exists(deployment_id: str) -> bool:
    """
    Check if a deployment exists.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        bool: True if deployment exists
    """
    deployment_dir = get_deployment_dir(deployment_id)
    return deployment_dir.exists() and (deployment_dir / "env.json").exists()


def cleanup_deployment(deployment_id: str) -> None:
    """
    Remove deployment directory and all its contents.
    
    Args:
        deployment_id: Deployment ID
    """
    deployment_dir = get_deployment_dir(deployment_id)
    
    if deployment_dir.exists():
        import shutil
        shutil.rmtree(deployment_dir)
