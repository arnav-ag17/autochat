"""
Mapping and canonicalization helpers for NLP extraction.
"""

from typing import Dict, List, Optional, Tuple


# Infrastructure synonyms (bi-directional maps)
INFRA_SYNONYMS = {
    "ec2": ["vm", "virtual machine", "ec2", "instance"],
    "ecs_fargate": ["container", "docker", "ecs", "fargate", "containers"],
    "lightsail_containers": ["lightsail containers", "lightsail container"],
    "s3_cf": ["static site", "cdn", "cloudfront", "s3 website", "static"],
    "lambda": ["serverless", "lambda", "function", "functions"]
}

# Reverse mapping for lookup
INFRA_LOOKUP = {}
for canonical, synonyms in INFRA_SYNONYMS.items():
    for synonym in synonyms:
        INFRA_LOOKUP[synonym.lower()] = canonical


# Region aliases
REGION_ALIASES = {
    "oregon": "us-west-2",
    "n. virginia": "us-east-1", 
    "northern virginia": "us-east-1",
    "frankfurt": "eu-central-1",
    "ireland": "eu-west-1",
    "london": "eu-west-2",
    "tokyo": "ap-northeast-1",
    "singapore": "ap-southeast-1",
    "sydney": "ap-southeast-2",
    "mumbai": "ap-south-1",
    "seoul": "ap-northeast-2",
    "california": "us-west-1",
    "ohio": "us-east-2",
    "canada": "ca-central-1",
    "sao paulo": "sa-east-1"
}

# Reverse mapping for region lookup
REGION_LOOKUP = {alias.lower(): canonical for alias, canonical in REGION_ALIASES.items()}


# Size tier mappings
SIZE_TIERS = {
    "nano": ["t3.nano", "t4g.nano"],
    "micro": ["t3.micro", "t4g.micro"],
    "small": ["t3.small", "t4g.small", "c6g.small"],
    "medium": ["t3.medium", "t4g.medium", "c6g.medium", "m5.medium"],
    "large": ["t3.large", "t4g.large", "c6g.large", "m5.large", "r5.large"],
    "xlarge": ["t3.xlarge", "t4g.xlarge", "c6g.xlarge", "m5.xlarge", "r5.xlarge"]
}

# Reverse mapping for instance type to size
INSTANCE_TYPE_TO_SIZE = {}
for size, types in SIZE_TIERS.items():
    for inst_type in types:
        INSTANCE_TYPE_TO_SIZE[inst_type] = size


def normalize_infra(infra: str) -> Optional[str]:
    """Normalize infrastructure type to canonical form."""
    if not infra:
        return None
    
    canonical = INFRA_LOOKUP.get(infra.lower())
    return canonical if canonical else infra


def normalize_region(region: str) -> Optional[str]:
    """Normalize region to canonical form."""
    if not region:
        return None
    
    # Check if already canonical
    if _is_canonical_region(region):
        return region
    
    # Check aliases
    canonical = REGION_LOOKUP.get(region.lower())
    return canonical if canonical else None


def normalize_instance_type(instance_type: str) -> Tuple[Optional[str], Optional[str]]:
    """Normalize instance type and infer size."""
    if not instance_type:
        return None, None
    
    # Check if it's already a valid instance type
    if _is_valid_instance_type(instance_type):
        size = INSTANCE_TYPE_TO_SIZE.get(instance_type)
        return instance_type, size
    
    return None, None


def infer_instance_size(instance_type: str) -> Optional[str]:
    """Infer instance size from instance type."""
    if not instance_type:
        return None
    
    return INSTANCE_TYPE_TO_SIZE.get(instance_type)


def get_default_instance_type(size: str) -> Optional[str]:
    """Get default instance type for a size tier."""
    if not size:
        return None
    
    types = SIZE_TIERS.get(size)
    return types[0] if types else None


def validate_and_normalize_overrides(overrides, assumptions: List[str]) -> Tuple[Dict, List[str]]:
    """Validate and normalize overrides, returning normalized dict and updated assumptions."""
    normalized = {}
    issues = []
    
    # Normalize infrastructure
    if overrides.get("infra"):
        normalized_infra = normalize_infra(overrides["infra"])
        if normalized_infra:
            normalized["infra"] = normalized_infra
        else:
            issues.append(f"Unknown infrastructure type: {overrides['infra']}")
            assumptions.append(f"Unknown infrastructure '{overrides['infra']}', leaving null")
    
    # Normalize region
    if overrides.get("region"):
        normalized_region = normalize_region(overrides["region"])
        if normalized_region:
            normalized["region"] = normalized_region
        else:
            issues.append(f"Unknown region: {overrides['region']}")
            assumptions.append(f"Unknown region '{overrides['region']}', leaving null")
    
    # Normalize instance type and infer size
    if overrides.get("instance_type"):
        inst_type, size = normalize_instance_type(overrides["instance_type"])
        if inst_type:
            normalized["instance_type"] = inst_type
            if size and not overrides.get("instance_size"):
                normalized["instance_size"] = size
        else:
            issues.append(f"Invalid instance type: {overrides['instance_type']}")
            assumptions.append(f"Invalid instance type '{overrides['instance_type']}', leaving null")
    
    # Infer instance type from size if not provided
    if overrides.get("instance_size") and not overrides.get("instance_type"):
        default_type = get_default_instance_type(overrides["instance_size"])
        if default_type:
            normalized["instance_type"] = default_type
            assumptions.append(f"Inferred instance type '{default_type}' from size '{overrides['instance_size']}'")
    
    # Copy other fields as-is
    for key in ["cloud", "containerized", "domain", "ssl", "autoscale", 
                "min_instances", "max_instances", "port", "health_path", 
                "env_overrides", "ttl_hours", "notes", "confidence", "instance_size"]:
        if key in overrides:
            normalized[key] = overrides[key]
    
    # Handle database config
    if overrides.get("db"):
        db_config = overrides["db"]
        if isinstance(db_config, dict):
            normalized["db"] = db_config
        else:
            issues.append("Invalid database configuration")
    
    return normalized, issues


def _is_canonical_region(region: str) -> bool:
    """Check if region is in canonical AWS format."""
    import re
    return bool(re.match(r'^[a-z]{2}-[a-z]+-\d+$', region))


def _is_valid_instance_type(instance_type: str) -> bool:
    """Check if instance type is valid."""
    import re
    # Basic AWS instance type pattern
    return bool(re.match(r'^[a-z]\d+[a-z]*\.[a-z]+$', instance_type))


def get_available_regions() -> List[str]:
    """Get list of available AWS regions."""
    return [
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1",
        "ap-northeast-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
        "ap-south-1", "ca-central-1", "sa-east-1"
    ]


def get_available_infra_types() -> List[str]:
    """Get list of available infrastructure types."""
    return list(INFRA_SYNONYMS.keys())


def get_available_sizes() -> List[str]:
    """Get list of available instance sizes."""
    return list(SIZE_TIERS.keys())


def get_region_aliases() -> Dict[str, str]:
    """Get mapping of region aliases to canonical names."""
    return REGION_ALIASES.copy()


def get_infra_synonyms() -> Dict[str, List[str]]:
    """Get mapping of infrastructure types to synonyms."""
    return INFRA_SYNONYMS.copy()
