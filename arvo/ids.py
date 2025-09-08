"""
Deployment ID generation utilities.
"""

import random
import string
from datetime import datetime


def new_deployment_id() -> str:
    """
    Generate a new deployment ID in format: d-YYYYMMDD-hhmmss-XXXX
    
    Returns:
        str: Unique deployment ID
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    
    # Generate 4 random alphanumeric characters
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    return f"d-{date_str}-{time_str}-{random_suffix}"


def is_valid_deployment_id(deployment_id: str) -> bool:
    """
    Validate deployment ID format.
    
    Args:
        deployment_id: ID to validate
        
    Returns:
        bool: True if valid format
    """
    if not deployment_id.startswith("d-"):
        return False
    
    parts = deployment_id.split("-")
    if len(parts) != 4:
        return False
    
    # Check date format (YYYYMMDD)
    if len(parts[1]) != 8 or not parts[1].isdigit():
        return False
    
    # Check time format (HHMMSS)
    if len(parts[2]) != 6 or not parts[2].isdigit():
        return False
    
    # Check random suffix (4 alphanumeric)
    if len(parts[3]) != 4:
        return False
    
    return True
