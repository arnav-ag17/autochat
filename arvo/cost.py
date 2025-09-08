"""
Cost estimation utilities for deployment cost awareness.
"""

import subprocess
import json
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


def estimate_cost(stack_path: str, region: str = "us-west-2") -> Dict[str, Any]:
    """
    Estimate deployment cost using available methods.
    
    Args:
        stack_path: Path to Terraform stack directory
        region: AWS region
        
    Returns:
        Cost estimation dictionary
    """
    # Try Infracost first (most accurate)
    infracost_result = _try_infracost(stack_path)
    if infracost_result:
        return infracost_result
    
    # Fallback to heuristic estimation
    return _heuristic_cost_estimate(stack_path, region)


def _try_infracost(stack_path: str) -> Optional[Dict[str, Any]]:
    """
    Try to get cost estimate using Infracost CLI.
    
    Args:
        stack_path: Path to Terraform stack directory
        
    Returns:
        Cost estimation if successful, None otherwise
    """
    try:
        # Check if infracost is available
        subprocess.run(['infracost', '--version'], 
                      capture_output=True, check=True)
        
        # Run infracost breakdown
        result = subprocess.run([
            'infracost', 'breakdown',
            '--path', stack_path,
            '--format', 'json'
        ], capture_output=True, text=True, check=True)
        
        data = json.loads(result.stdout)
        
        # Extract monthly cost
        total_monthly = 0.0
        for project in data.get('projects', []):
            for resource in project.get('breakdown', {}).get('resources', []):
                monthly_cost = resource.get('monthlyCost', 0)
                if monthly_cost:
                    total_monthly += float(monthly_cost)
        
        return {
            "method": "infracost",
            "monthly_usd": round(total_monthly, 2),
            "currency": "USD",
            "details": data
        }
    
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None


def _heuristic_cost_estimate(stack_path: str, region: str) -> Dict[str, Any]:
    """
    Provide heuristic cost estimate based on Terraform configuration.
    
    Args:
        stack_path: Path to Terraform stack directory
        region: AWS region
        
    Returns:
        Heuristic cost estimation
    """
    # Read terraform.tfvars.json if it exists
    tfvars_path = Path(stack_path) / "terraform.tfvars.json"
    tfvars = {}
    
    if tfvars_path.exists():
        try:
            with open(tfvars_path, 'r') as f:
                tfvars = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Analyze the stack type and provide estimates
    stack_name = Path(stack_path).name
    
    if stack_name == "ec2_web":
        return _estimate_ec2_cost(tfvars)
    elif stack_name == "ecs_web":
        return _estimate_ecs_cost(tfvars)
    elif stack_name == "static_site":
        return _estimate_static_cost(tfvars)
    else:
        return {
            "method": "heuristic",
            "monthly_usd": None,
            "currency": "USD",
            "hint": "Unknown stack type - cost estimation not available"
        }


def _estimate_ec2_cost(tfvars: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate EC2 deployment cost."""
    instance_type = tfvars.get("instance_type", "t3.micro")
    
    # Rough hourly costs (these are approximate and may vary by region)
    hourly_costs = {
        "t3.micro": 0.0104,    # ~$7.50/month
        "t3.small": 0.0208,    # ~$15/month
        "t3.medium": 0.0416,   # ~$30/month
        "t3.large": 0.0832,    # ~$60/month
        "t3.xlarge": 0.1664,   # ~$120/month
    }
    
    hourly_cost = hourly_costs.get(instance_type, 0.0104)
    monthly_cost = hourly_cost * 24 * 30  # Rough monthly estimate
    
    return {
        "method": "heuristic",
        "monthly_usd": round(monthly_cost, 2),
        "currency": "USD",
        "hint": f"EC2 {instance_type} instance (~${hourly_cost:.3f}/hour)",
        "breakdown": {
            "ec2_instance": f"~${monthly_cost:.2f}/month",
            "eip": "~$3.65/month (if allocated)",
            "data_transfer": "varies by usage"
        }
    }


def _estimate_ecs_cost(tfvars: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate ECS deployment cost."""
    cpu = tfvars.get("cpu", 256)  # Default Fargate CPU
    memory = tfvars.get("memory", 512)  # Default Fargate memory
    
    # Fargate pricing (approximate)
    cpu_per_vcpu_hour = 0.04048
    memory_per_gb_hour = 0.004445
    
    vcpus = cpu / 1024  # Convert CPU units to vCPUs
    gb_memory = memory / 1024  # Convert MB to GB
    
    hourly_cost = (vcpus * cpu_per_vcpu_hour) + (gb_memory * memory_per_gb_hour)
    monthly_cost = hourly_cost * 24 * 30
    
    return {
        "method": "heuristic",
        "monthly_usd": round(monthly_cost, 2),
        "currency": "USD",
        "hint": f"ECS Fargate task ({cpu} CPU, {memory} MB memory)",
        "breakdown": {
            "fargate_task": f"~${monthly_cost:.2f}/month",
            "alb": "~$16/month",
            "data_transfer": "varies by usage"
        }
    }


def _estimate_static_cost(tfvars: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate static site deployment cost."""
    return {
        "method": "heuristic",
        "monthly_usd": 1.0,  # Very low cost for static sites
        "currency": "USD",
        "hint": "Static site with S3 + CloudFront",
        "breakdown": {
            "s3_storage": "~$0.023/GB/month",
            "s3_requests": "~$0.0004/1000 requests",
            "cloudfront": "~$0.085/GB transfer (first 10TB)",
            "note": "Costs are very low unless high traffic"
        }
    }


def format_cost_hint(cost_data: Dict[str, Any]) -> str:
    """
    Format cost data into a human-readable hint.
    
    Args:
        cost_data: Cost estimation data
        
    Returns:
        Formatted cost hint string
    """
    method = cost_data.get("method", "unknown")
    monthly_usd = cost_data.get("monthly_usd")
    hint = cost_data.get("hint", "")
    
    if monthly_usd is not None:
        if monthly_usd < 1:
            cost_str = f"~${monthly_usd:.2f}/month"
        elif monthly_usd < 10:
            cost_str = f"~${monthly_usd:.1f}/month"
        else:
            cost_str = f"~${monthly_usd:.0f}/month"
        
        if hint:
            return f"💰 Estimated cost: {cost_str} ({hint})"
        else:
            return f"💰 Estimated cost: {cost_str}"
    else:
        if hint:
            return f"💰 Cost hint: {hint}"
        else:
            return "💰 Cost estimation not available"


def should_show_cost_warning(monthly_usd: Optional[float], threshold: float = 50.0) -> bool:
    """
    Determine if a cost warning should be shown.
    
    Args:
        monthly_usd: Monthly cost in USD
        threshold: Warning threshold in USD
        
    Returns:
        True if warning should be shown
    """
    return monthly_usd is not None and monthly_usd > threshold
