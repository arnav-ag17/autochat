"""
TTL (Time To Live) management for automatic deployment cleanup.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .state import get_deployment_dir, list_deployments
from .tags import is_expired
# Note: We'll import destroy dynamically to avoid circular imports

logger = logging.getLogger(__name__)


def schedule_ttl_deployment(deployment_id: str, ttl_hours: int) -> Dict[str, Any]:
    """
    Schedule a deployment for TTL-based auto-destruction.
    
    Args:
        deployment_id: Deployment ID
        ttl_hours: TTL in hours
        
    Returns:
        TTL scheduling information
    """
    deployment_dir = get_deployment_dir(deployment_id)
    ttl_file = deployment_dir / "ttl.json"
    
    expires_at = datetime.utcnow().timestamp() + (ttl_hours * 3600)
    expires_iso = datetime.fromtimestamp(expires_at).isoformat() + "Z"
    
    ttl_data = {
        "deployment_id": deployment_id,
        "ttl_hours": ttl_hours,
        "scheduled_at": datetime.utcnow().isoformat() + "Z",
        "expires_at": expires_iso,
        "expires_timestamp": expires_at
    }
    
    # Write TTL data to deployment directory
    with open(ttl_file, 'w') as f:
        json.dump(ttl_data, f, indent=2)
    
    # Also write to global TTL registry
    _update_global_ttl_registry(deployment_id, ttl_data)
    
    return ttl_data


def run_ttl_sweep() -> Dict[str, Any]:
    """
    Run TTL sweep to destroy expired deployments.
    
    Returns:
        Sweep results
    """
    expired_deployments = []
    destroyed_count = 0
    failed_count = 0
    
    # Get all deployments
    deployment_ids = list_deployments()
    
    for deployment_id in deployment_ids:
        try:
            # Check if deployment has TTL
            ttl_data = _get_ttl_data(deployment_id)
            if not ttl_data:
                continue
            
            # Check if expired
            if _is_deployment_expired(ttl_data):
                expired_deployments.append(deployment_id)
                
                logger.info(f"Deployment {deployment_id} has expired, destroying...")
                
                try:
                    # Destroy the deployment (import dynamically to avoid circular imports)
                    from .orchestrator import destroy
                    result = destroy(deployment_id)
                    
                    if result.get("status") == "destroyed":
                        destroyed_count += 1
                        logger.info(f"Successfully destroyed expired deployment {deployment_id}")
                    else:
                        failed_count += 1
                        logger.error(f"Failed to destroy expired deployment {deployment_id}: {result}")
                
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Exception destroying expired deployment {deployment_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error checking TTL for deployment {deployment_id}: {e}")
    
    return {
        "expired_deployments": expired_deployments,
        "destroyed_count": destroyed_count,
        "failed_count": failed_count,
        "total_checked": len(deployment_ids)
    }


def _get_ttl_data(deployment_id: str) -> Optional[Dict[str, Any]]:
    """Get TTL data for a deployment."""
    try:
        deployment_dir = get_deployment_dir(deployment_id)
        ttl_file = deployment_dir / "ttl.json"
        
        if ttl_file.exists():
            with open(ttl_file, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


def _is_deployment_expired(ttl_data: Dict[str, Any]) -> bool:
    """Check if a deployment is expired based on TTL data."""
    try:
        expires_timestamp = ttl_data.get("expires_timestamp")
        if expires_timestamp:
            return time.time() > expires_timestamp
        
        # Fallback to ISO string parsing
        expires_at = ttl_data.get("expires_at")
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return datetime.utcnow().replace(tzinfo=expires_dt.tzinfo) > expires_dt
    except (ValueError, TypeError):
        pass
    
    return False


def _update_global_ttl_registry(deployment_id: str, ttl_data: Dict[str, Any]) -> None:
    """Update global TTL registry."""
    try:
        # Create .arvo directory if it doesn't exist
        arvo_dir = Path(".arvo")
        arvo_dir.mkdir(exist_ok=True)
        
        ttl_registry_file = arvo_dir / "ttl.json"
        
        # Load existing registry
        registry = {}
        if ttl_registry_file.exists():
            try:
                with open(ttl_registry_file, 'r') as f:
                    registry = json.load(f)
            except (json.JSONDecodeError, IOError):
                registry = {}
        
        # Update registry
        registry[deployment_id] = ttl_data
        
        # Write back to file
        with open(ttl_registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
    
    except Exception as e:
        logger.warning(f"Failed to update global TTL registry: {e}")


def list_ttl_deployments() -> List[Dict[str, Any]]:
    """
    List all deployments with TTL information.
    
    Returns:
        List of TTL deployment information
    """
    ttl_deployments = []
    
    try:
        arvo_dir = Path(".arvo")
        ttl_registry_file = arvo_dir / "ttl.json"
        
        if ttl_registry_file.exists():
            with open(ttl_registry_file, 'r') as f:
                registry = json.load(f)
            
            for deployment_id, ttl_data in registry.items():
                # Check if deployment still exists
                deployment_dir = get_deployment_dir(deployment_id)
                if deployment_dir.exists():
                    ttl_data["exists"] = True
                    ttl_data["expired"] = _is_deployment_expired(ttl_data)
                else:
                    ttl_data["exists"] = False
                    ttl_data["expired"] = False
                
                ttl_deployments.append(ttl_data)
    
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to read TTL registry: {e}")
    
    return ttl_deployments


def cancel_ttl(deployment_id: str) -> bool:
    """
    Cancel TTL for a deployment.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        True if TTL was cancelled, False otherwise
    """
    try:
        # Remove TTL file from deployment directory
        deployment_dir = get_deployment_dir(deployment_id)
        ttl_file = deployment_dir / "ttl.json"
        
        if ttl_file.exists():
            ttl_file.unlink()
        
        # Remove from global registry
        arvo_dir = Path(".arvo")
        ttl_registry_file = arvo_dir / "ttl.json"
        
        if ttl_registry_file.exists():
            with open(ttl_registry_file, 'r') as f:
                registry = json.load(f)
            
            if deployment_id in registry:
                del registry[deployment_id]
                
                with open(ttl_registry_file, 'w') as f:
                    json.dump(registry, f, indent=2)
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to cancel TTL for deployment {deployment_id}: {e}")
        return False
