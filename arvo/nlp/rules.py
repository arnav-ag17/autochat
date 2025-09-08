"""
Deterministic regex/phrase rules for Pass A extraction.
"""

import re
from typing import Dict, List, Optional, Tuple
from .schema import Overrides, DatabaseConfig


def extract_pass_a(instructions: str) -> Tuple[Overrides, List[str]]:
    """
    Extract deployment overrides using deterministic rules (Pass A).
    
    Args:
        instructions: Raw instruction text
        
    Returns:
        Tuple of (partial_overrides, hits) where hits are the rules that fired
    """
    text = instructions.lower()
    hits = []
    overrides = Overrides()
    
    # Cloud provider detection
    cloud = _extract_cloud(text, hits)
    if cloud:
        overrides.cloud = cloud
    
    # Infrastructure type detection
    infra = _extract_infra(text, hits)
    if infra:
        overrides.infra = infra
    
    # Region detection
    region = _extract_region(text, hits)
    if region:
        overrides.region = region
    
    # Instance size detection
    instance_size, instance_type = _extract_instance_size(text, hits)
    if instance_size:
        overrides.instance_size = instance_size
    if instance_type:
        overrides.instance_type = instance_type
    
    # Containerization detection
    containerized = _extract_containerized(text, hits)
    if containerized is not None:
        overrides.containerized = containerized
    
    # Domain detection
    domain = _extract_domain(text, hits)
    if domain:
        overrides.domain = domain
    
    # SSL detection
    ssl = _extract_ssl(text, hits)
    if ssl is not None:
        overrides.ssl = ssl
    
    # Autoscaling detection
    autoscale, min_inst, max_inst = _extract_autoscaling(text, hits)
    if autoscale is not None:
        overrides.autoscale = autoscale
    if min_inst:
        overrides.min_instances = min_inst
    if max_inst:
        overrides.max_instances = max_inst
    
    # Database detection
    db_config = _extract_database(text, hits)
    if db_config:
        overrides.db = db_config
    
    # Port detection
    port = _extract_port(text, hits)
    if port:
        overrides.port = port
    
    # Health path detection
    health_path = _extract_health_path(text, hits)
    if health_path:
        overrides.health_path = health_path
    
    # Environment variables detection
    env_overrides = _extract_env_vars(text, hits)
    if env_overrides:
        overrides.env_overrides = env_overrides
    
    # TTL detection
    ttl_hours = _extract_ttl(text, hits)
    if ttl_hours:
        overrides.ttl_hours = ttl_hours
    
    return overrides, hits


def _extract_cloud(text: str, hits: List[str]) -> Optional[str]:
    """Extract cloud provider from text."""
    patterns = [
        (r'\bon aws\b|\bamazon\b|\baws\b', "aws"),
        (r'\bon gcp\b|\bgoogle cloud\b|\bgcp\b', "gcp"),
        (r'\bon azure\b|\bmicrosoft azure\b|\bazure\b', "azure")
    ]
    
    for pattern, cloud in patterns:
        if re.search(pattern, text):
            hits.append(f"cloud:{cloud}")
            return cloud
    return None


def _extract_infra(text: str, hits: List[str]) -> Optional[str]:
    """Extract infrastructure type from text."""
    patterns = [
        (r'\bserverless\b|\blambda\b|\bfunction\b', "lambda"),
        (r'\bvm\b|\bvirtual machine\b|\bec2\b', "ec2"),
        (r'\bcontainer\b|\bcontainerize\b|\bdocker\b|\becs\b|\bfargate\b|\blightsail containers?\b', "ecs_fargate"),
        (r'\bstatic site\b|\bcdn\b|\bcloudfront\b|\bs3 website\b', "s3_cf")
    ]
    
    for pattern, infra in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(f"infra:{infra}")
            return infra
    return None


def _extract_region(text: str, hits: List[str]) -> Optional[str]:
    """Extract region from text."""
    # Direct region patterns
    region_pattern = r'\b(us-[a-z]+-\d+|eu-[a-z]+-\d+|ap-[a-z]+-\d+|ca-[a-z]+-\d+|sa-[a-z]+-\d+)\b'
    match = re.search(region_pattern, text)
    if match:
        hits.append(f"region:direct:{match.group(1)}")
        return match.group(1)
    
    # Region aliases
    aliases = {
        'oregon': 'us-west-2',
        'n. virginia': 'us-east-1',
        'northern virginia': 'us-east-1',
        'frankfurt': 'eu-central-1',
        'ireland': 'eu-west-1',
        'london': 'eu-west-2',
        'tokyo': 'ap-northeast-1',
        'singapore': 'ap-southeast-1',
        'sydney': 'ap-southeast-2',
        'mumbai': 'ap-south-1',
        'seoul': 'ap-northeast-2',
        'california': 'us-west-1',
        'ohio': 'us-east-2'
    }
    
    for alias, canonical in aliases.items():
        if re.search(rf'\b{re.escape(alias)}\b', text):
            hits.append(f"region:alias:{alias}->{canonical}")
            return canonical
    
    return None


def _extract_instance_size(text: str, hits: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Extract instance size and type from text."""
    # Abstract size mappings
    size_patterns = [
        (r'\btiny\b|\bvery small\b', "micro"),
        (r'\bmicro\b', "micro"),
        (r'\bsmall\b', "small"),
        (r'\bmedium\b', "medium"),
        (r'\blarge\b', "large"),
        (r'\bxlarge\b|\bextra large\b', "xlarge")
    ]
    
    instance_size = None
    for pattern, size in size_patterns:
        if re.search(pattern, text):
            instance_size = size
            hits.append(f"size:abstract:{size}")
            break
    
    # Specific instance types
    instance_type_patterns = [
        (r'\bt3\.micro\b', "t3.micro"),
        (r'\bt3\.small\b', "t3.small"),
        (r'\bt3\.medium\b', "t3.medium"),
        (r'\bt3\.large\b', "t3.large"),
        (r'\bt3\.xlarge\b', "t3.xlarge"),
        (r'\bc6g\.large\b', "c6g.large"),
        (r'\bm5\.large\b', "m5.large"),
        (r'\br5\.large\b', "r5.large")
    ]
    
    instance_type = None
    for pattern, inst_type in instance_type_patterns:
        if re.search(pattern, text):
            instance_type = inst_type
            hits.append(f"type:specific:{inst_type}")
            # Infer size from type if not already set
            if not instance_size:
                size_map = {
                    't3.micro': 'micro',
                    't3.small': 'small', 
                    't3.medium': 'medium',
                    't3.large': 'large',
                    't3.xlarge': 'xlarge',
                    'c6g.large': 'large',
                    'm5.large': 'large',
                    'r5.large': 'large'
                }
                instance_size = size_map.get(inst_type)
            break
    
    return instance_size, instance_type


def _extract_containerized(text: str, hits: List[str]) -> Optional[bool]:
    """Extract containerization preference from text."""
    container_patterns = [
        r'\bcontaineriz\w+\b',
        r'\bdocker\b',
        r'\bcontainer\b'
    ]
    
    for pattern in container_patterns:
        if re.search(pattern, text):
            hits.append("containerized:true")
            return True
    
    return None


def _extract_domain(text: str, hits: List[str]) -> Optional[str]:
    """Extract domain from text."""
    # Domain patterns
    domain_patterns = [
        r'\bdomain\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        r'\bcustom domain\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        r'\b([a-zA-Z0-9.-]+\.(?:com|org|net|io|dev|app))\b'
    ]
    
    for pattern in domain_patterns:
        match = re.search(pattern, text)
        if match:
            domain = match.group(1)
            hits.append(f"domain:{domain}")
            return domain
    
    return None


def _extract_ssl(text: str, hits: List[str]) -> Optional[bool]:
    """Extract SSL/HTTPS preference from text."""
    ssl_patterns = [
        r'\bhttps\b',
        r'\bssl\b',
        r'\btls\b',
        r'\bsecure\b'
    ]
    
    for pattern in ssl_patterns:
        if re.search(pattern, text):
            hits.append("ssl:true")
            return True
    
    return None


def _extract_autoscaling(text: str, hits: List[str]) -> Tuple[Optional[bool], Optional[int], Optional[int]]:
    """Extract autoscaling configuration from text."""
    autoscale = None
    min_inst = None
    max_inst = None
    
    # Autoscaling detection
    if re.search(r'\bautoscaling\b', text):
        autoscale = True
        hits.append("autoscale:true")
    
    # Min instances
    min_match = re.search(r'\bmin\s+(\d+)\b', text)
    if min_match:
        min_inst = int(min_match.group(1))
        hits.append(f"min_instances:{min_inst}")
        autoscale = True  # If min instances specified, enable autoscaling
    
    # Max instances
    max_match = re.search(r'\bmax\s+(\d+)\b', text)
    if max_match:
        max_inst = int(max_match.group(1))
        hits.append(f"max_instances:{max_inst}")
        autoscale = True  # If max instances specified, enable autoscaling
    
    # Scale range
    range_match = re.search(r'\bscale\s+to\s+(\d+)\b', text)
    if range_match:
        max_inst = int(range_match.group(1))
        hits.append(f"scale_to:{max_inst}")
        autoscale = True  # If scale specified, enable autoscaling
    
    # Instance range
    range_match = re.search(r'\b(\d+)\s*\.\.\s*(\d+)\b', text)
    if range_match:
        min_inst = int(range_match.group(1))
        max_inst = int(range_match.group(2))
        hits.append(f"range:{min_inst}-{max_inst}")
        autoscale = True  # If range specified, enable autoscaling
    
    return autoscale, min_inst, max_inst


def _extract_database(text: str, hits: List[str]) -> Optional[DatabaseConfig]:
    """Extract database configuration from text."""
    db_patterns = [
        (r'\bwith postgres\b|\bpostgresql\b', "postgres"),
        (r'\bwith mysql\b', "mysql"),
        (r'\bwith sqlite\b', "sqlite"),
        (r'\bno db\b|\bno database\b|\bwithout database\b', "none")
    ]
    
    for pattern, engine in db_patterns:
        if re.search(pattern, text):
            hits.append(f"db:{engine}")
            return DatabaseConfig(engine=engine)
    
    return None


def _extract_port(text: str, hits: List[str]) -> Optional[int]:
    """Extract port from text."""
    port_match = re.search(r'\bport\s+(\d+)\b', text)
    if port_match:
        port = int(port_match.group(1))
        hits.append(f"port:{port}")
        return port
    return None


def _extract_health_path(text: str, hits: List[str]) -> Optional[str]:
    """Extract health check path from text."""
    health_patterns = [
        r'\bhealth\s+(?:path\s+)?(/\S*)',
        r'\bhealth\s+check\s+(?:path\s+)?(/\S*)'
    ]
    
    for pattern in health_patterns:
        match = re.search(pattern, text)
        if match:
            path = match.group(1)
            hits.append(f"health_path:{path}")
            return path
    
    return None


def _extract_env_vars(text: str, hits: List[str]) -> Optional[Dict[str, str]]:
    """Extract environment variables from text."""
    env_vars = {}
    
    # Conservative pattern for uppercase environment variables (case insensitive)
    env_pattern = r'\b([A-Z][A-Z0-9_]*)\s*=\s*([^\s,]+)'
    matches = re.findall(env_pattern, text, re.IGNORECASE)
    
    for key, value in matches:
        env_vars[key.upper()] = value  # Normalize to uppercase
        hits.append(f"env:{key.upper()}={value}")
    
    return env_vars if env_vars else None


def _extract_ttl(text: str, hits: List[str]) -> Optional[int]:
    """Extract TTL from text."""
    ttl_patterns = [
        r'\b(\d+)\s*h\b',  # 24h
        r'\b(\d+)\s*hours?\b',  # 24 hours
        r'\bauto-destroy\s+in\s+(\d+)\s*h\b',  # auto-destroy in 24h
        r'\bttl\s+(\d+)\s*h\b'  # ttl 24h
    ]
    
    for pattern in ttl_patterns:
        match = re.search(pattern, text)
        if match:
            ttl = int(match.group(1))
            hits.append(f"ttl:{ttl}h")
            return ttl
    
    return None
