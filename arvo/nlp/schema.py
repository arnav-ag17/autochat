"""
JSON Schema and dataclasses for NLP extraction results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json


# JSON Schema for structured LLM output
OVERRIDES_SCHEMA = {
    "type": "object",
    "properties": {
        "cloud": {
            "type": "string",
            "enum": ["aws", "gcp", "azure"],
            "description": "Cloud provider"
        },
        "infra": {
            "type": "string", 
            "enum": ["ec2", "ecs_fargate", "lightsail_containers", "s3_cf", "lambda"],
            "description": "Infrastructure type"
        },
        "region": {
            "type": "string",
            "description": "AWS region (e.g., us-west-2)"
        },
        "instance_size": {
            "type": "string",
            "enum": ["nano", "micro", "small", "medium", "large", "xlarge"],
            "description": "Abstract instance size tier"
        },
        "instance_type": {
            "type": "string",
            "description": "Specific instance type (e.g., t3.small)"
        },
        "containerized": {
            "type": "boolean",
            "description": "Whether to use containers"
        },
        "domain": {
            "type": "string",
            "description": "Custom domain name"
        },
        "ssl": {
            "type": "boolean",
            "description": "Enable SSL/HTTPS"
        },
        "autoscale": {
            "type": "boolean",
            "description": "Enable autoscaling"
        },
        "min_instances": {
            "type": "integer",
            "minimum": 1,
            "description": "Minimum number of instances"
        },
        "max_instances": {
            "type": "integer",
            "minimum": 1,
            "description": "Maximum number of instances"
        },
        "port": {
            "type": "integer",
            "minimum": 1,
            "maximum": 65535,
            "description": "Application port"
        },
        "health_path": {
            "type": "string",
            "description": "Health check path"
        },
        "db": {
            "type": "object",
            "properties": {
                "engine": {
                    "type": "string",
                    "enum": ["postgres", "mysql", "sqlite", "none"],
                    "description": "Database engine"
                },
                "size": {
                    "type": "string",
                    "description": "Database size/instance type"
                }
            },
            "description": "Database configuration"
        },
        "env_overrides": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Environment variable overrides"
        },
        "ttl_hours": {
            "type": "integer",
            "minimum": 1,
            "description": "Time to live in hours"
        },
        "notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Free-form hints and notes"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Overall confidence score"
        }
    },
    "additionalProperties": False
}


@dataclass
class DatabaseConfig:
    """Database configuration."""
    engine: Optional[str] = None  # "postgres", "mysql", "sqlite", "none"
    size: Optional[str] = None    # Database instance size


@dataclass
class Overrides:
    """Normalized deployment overrides extracted from instructions."""
    # Cloud and infrastructure
    cloud: Optional[str] = None                    # "aws", "gcp", "azure"
    infra: Optional[str] = None                    # "ec2", "ecs_fargate", "lightsail_containers", "s3_cf", "lambda"
    region: Optional[str] = None                   # Canonical region like "us-west-2"
    
    # Instance configuration
    instance_size: Optional[str] = None            # "nano", "micro", "small", "medium", "large", "xlarge"
    instance_type: Optional[str] = None            # Specific type like "t3.small"
    containerized: Optional[bool] = None           # Whether to use containers
    
    # Networking and security
    domain: Optional[str] = None                   # Custom domain name
    ssl: Optional[bool] = None                     # Enable SSL/HTTPS
    
    # Scaling
    autoscale: Optional[bool] = None               # Enable autoscaling
    min_instances: Optional[int] = None            # Minimum instances
    max_instances: Optional[int] = None            # Maximum instances
    
    # Application configuration
    port: Optional[int] = None                     # Application port
    health_path: Optional[str] = None              # Health check path
    db: Optional[DatabaseConfig] = None            # Database configuration
    
    # Environment and lifecycle
    env_overrides: Optional[Dict[str, str]] = None # Environment variable overrides
    ttl_hours: Optional[int] = None                # Time to live in hours
    
    # Metadata
    notes: List[str] = field(default_factory=list) # Free-form hints
    confidence: float = 0.5                        # Overall confidence (0.0-1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if field_value is not None:
                if field_name == "db" and isinstance(field_value, DatabaseConfig):
                    result[field_name] = {
                        "engine": field_value.engine,
                        "size": field_value.size
                    }
                else:
                    result[field_name] = field_value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Overrides":
        """Create from dictionary."""
        # Handle database config
        db_config = None
        if "db" in data and data["db"]:
            db_data = data["db"]
            db_config = DatabaseConfig(
                engine=db_data.get("engine"),
                size=db_data.get("size")
            )
        
        return cls(
            cloud=data.get("cloud"),
            infra=data.get("infra"),
            region=data.get("region"),
            instance_size=data.get("instance_size"),
            instance_type=data.get("instance_type"),
            containerized=data.get("containerized"),
            domain=data.get("domain"),
            ssl=data.get("ssl"),
            autoscale=data.get("autoscale"),
            min_instances=data.get("min_instances"),
            max_instances=data.get("max_instances"),
            port=data.get("port"),
            health_path=data.get("health_path"),
            db=db_config,
            env_overrides=data.get("env_overrides"),
            ttl_hours=data.get("ttl_hours"),
            notes=data.get("notes", []),
            confidence=data.get("confidence", 0.5)
        )


@dataclass
class NLPReport:
    """Report of NLP extraction process and results."""
    assumptions: List[str] = field(default_factory=list)  # Defaults chosen
    conflicts: List[str] = field(default_factory=list)    # Conflicting requests
    raw_provider: str = ""                                # Provider used
    raw_text_used: str = ""                               # Final prompt text
    passA_hits: List[str] = field(default_factory=list)   # Deterministic rules that fired
    duration_ms: int = 0                                  # Total processing time
    confidence: float = 0.0                               # Overall confidence score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "assumptions": self.assumptions,
            "conflicts": self.conflicts,
            "raw_provider": self.raw_provider,
            "raw_text_used": self.raw_text_used,
            "passA_hits": self.passA_hits,
            "duration_ms": self.duration_ms,
            "confidence": self.confidence
        }


def validate_overrides(overrides: Overrides) -> List[str]:
    """Validate overrides and return list of issues."""
    issues = []
    
    # Validate region format if provided
    if overrides.region and not _is_valid_region(overrides.region):
        issues.append(f"Invalid region format: {overrides.region}")
    
    # Validate domain format if provided
    if overrides.domain and not _is_valid_domain(overrides.domain):
        issues.append(f"Invalid domain format: {overrides.domain}")
    
    # Validate port range if provided
    if overrides.port and (overrides.port < 1 or overrides.port > 65535):
        issues.append(f"Invalid port: {overrides.port}")
    
    # Validate instance counts
    if overrides.min_instances and overrides.min_instances < 1:
        issues.append(f"Invalid min_instances: {overrides.min_instances}")
    
    if overrides.max_instances and overrides.max_instances < 1:
        issues.append(f"Invalid max_instances: {overrides.max_instances}")
    
    if (overrides.min_instances and overrides.max_instances and 
        overrides.min_instances > overrides.max_instances):
        issues.append("min_instances cannot be greater than max_instances")
    
    # Validate TTL
    if overrides.ttl_hours and overrides.ttl_hours < 1:
        issues.append(f"Invalid ttl_hours: {overrides.ttl_hours}")
    
    # Validate confidence
    if overrides.confidence < 0.0 or overrides.confidence > 1.0:
        issues.append(f"Invalid confidence: {overrides.confidence}")
    
    return issues


def _is_valid_region(region: str) -> bool:
    """Check if region has valid AWS format."""
    # Basic AWS region format: xx-xxxx-x
    import re
    return bool(re.match(r'^[a-z]{2}-[a-z]+-\d+$', region))


def _is_valid_domain(domain: str) -> bool:
    """Check if domain has valid format."""
    import re
    # Basic domain validation: alphanumeric, dots, hyphens
    return bool(re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain))
