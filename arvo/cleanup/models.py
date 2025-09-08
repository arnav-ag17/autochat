"""
Data models for cleanup and resource management.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class FoundResource:
    """Represents a found AWS resource with tagging information."""
    service: str  # "ec2", "eip", "sg", "alb", "tg", "listener", "ecs", "ecr", "logs", "s3", "cloudfront", "iam", etc.
    arn_or_id: str
    tags: Dict[str, str]
    reason: Optional[str] = None  # Why we think it belongs to this deployment
