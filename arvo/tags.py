"""
Tagging utilities for consistent resource tagging across deployments.
"""

from datetime import datetime
from typing import Dict, Optional


def base_tags(deployment_id: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Generate base tags for a deployment.
    
    Args:
        deployment_id: Deployment ID
        extra: Additional tags to include
        
    Returns:
        Dictionary of tags to apply to resources
    """
    tags = {
        "project": "arvo",
        "deployment_id": deployment_id,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    # Add extra tags if provided
    if extra:
        tags.update(extra)
    
    return tags


def parse_user_tags(tag_strings: list[str]) -> Dict[str, str]:
    """
    Parse user-provided tag strings in format "key=value".
    
    Args:
        tag_strings: List of tag strings in "key=value" format
        
    Returns:
        Dictionary of parsed tags
        
    Raises:
        ValueError: If tag string format is invalid
    """
    tags = {}
    
    for tag_str in tag_strings:
        if "=" not in tag_str:
            raise ValueError(f"Invalid tag format: {tag_str}. Expected 'key=value'")
        
        key, value = tag_str.split("=", 1)
        if not key.strip() or not value.strip():
            raise ValueError(f"Invalid tag format: {tag_str}. Key and value must not be empty")
        
        tags[key.strip()] = value.strip()
    
    return tags


def add_ttl_tags(tags: Dict[str, str], ttl_hours: int) -> Dict[str, str]:
    """
    Add TTL-related tags to a tag dictionary.
    
    Args:
        tags: Base tags dictionary
        ttl_hours: TTL in hours
        
    Returns:
        Tags dictionary with TTL information added
    """
    expires_at = datetime.utcnow().timestamp() + (ttl_hours * 3600)
    expires_iso = datetime.fromtimestamp(expires_at).isoformat() + "Z"
    
    tags_with_ttl = tags.copy()
    tags_with_ttl["ttl_hours"] = str(ttl_hours)
    tags_with_ttl["expires_at"] = expires_iso
    
    return tags_with_ttl


def is_expired(tags: Dict[str, str]) -> bool:
    """
    Check if a resource is expired based on its tags.
    
    Args:
        tags: Resource tags
        
    Returns:
        True if resource is expired, False otherwise
    """
    if "expires_at" not in tags:
        return False
    
    try:
        expires_at = datetime.fromisoformat(tags["expires_at"].replace("Z", "+00:00"))
        return datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at
    except (ValueError, TypeError):
        return False


def get_deployment_id_from_tags(tags: Dict[str, str]) -> Optional[str]:
    """
    Extract deployment ID from resource tags.
    
    Args:
        tags: Resource tags
        
    Returns:
        Deployment ID if found, None otherwise
    """
    return tags.get("deployment_id")


def is_arvo_resource(tags: Dict[str, str]) -> bool:
    """
    Check if a resource belongs to Arvo based on its tags.
    
    Args:
        tags: Resource tags
        
    Returns:
        True if resource belongs to Arvo, False otherwise
    """
    return tags.get("project") == "arvo"
