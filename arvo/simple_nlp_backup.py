"""
Simple NLP system for extracting deployment requirements from natural language.
"""

import re
from typing import Dict, Any


def extract_deployment_requirements(instructions: str) -> Dict[str, Any]:
    """
    Extract deployment requirements from natural language instructions.
    
    Args:
        instructions: Natural language deployment instructions
        
    Returns:
        Dictionary with extracted requirements
    """
    text = instructions.lower()
    requirements = {
        "cloud": "aws",  # Default to AWS
        "infra": "vm",   # Default to VM
        "region": "us-west-2",  # Default region
        "instance_size": "small",  # Default size
        "framework": None,
        "port": None,
        "domain": None,
        "ssl": False,
        "autoscale": False,
        "database": False,
        "load_balancer": False,
        "monitoring": False
    }
    
    # Extract cloud provider
    if any(cloud in text for cloud in ['aws', 'amazon']):
        requirements["cloud"] = "aws"
    elif any(cloud in text for cloud in ['gcp', 'google', 'google cloud']):
        requirements["cloud"] = "gcp"
    elif any(cloud in text for cloud in ['azure', 'microsoft']):
        requirements["cloud"] = "azure"
    
    # Extract infrastructure type
    if any(infra in text for infra in ['serverless', 'lambda', 'functions']):
        requirements["infra"] = "serverless"
    elif any(infra in text for infra in ['kubernetes', 'k8s', 'container']):
        requirements["infra"] = "kubernetes"
    elif any(infra in text for infra in ['vm', 'virtual machine', 'ec2', 'instance']):
        requirements["infra"] = "vm"
    
    # Extract region
    if 'us-east' in text:
        requirements["region"] = "us-east-1"
    elif 'us-west' in text:
        requirements["region"] = "us-west-2"
    elif 'eu-west' in text:
        requirements["region"] = "eu-west-1"
    elif 'ap-south' in text:
        requirements["region"] = "ap-south-1"
    
    # Extract instance size
    if any(size in text for size in ['small', 'micro', 't2.micro']):
        requirements["instance_size"] = "small"
    elif any(size in text for size in ['medium', 't2.medium']):
        requirements["instance_size"] = "medium"
    elif any(size in text for size in ['large', 't2.large']):
        requirements["instance_size"] = "large"
    
    # Extract framework
    if any(fw in text for fw in ['flask', 'python flask']):
        requirements["framework"] = "flask"
    elif any(fw in text for fw in ['django', 'python django']):
        requirements["framework"] = "django"
    elif any(fw in text for fw in ['fastapi', 'python fastapi']):
        requirements["framework"] = "fastapi"
    elif any(fw in text for fw in ['express', 'node express', 'nodejs']):
        requirements["framework"] = "express"
    elif any(fw in text for fw in ['next', 'nextjs', 'next.js']):
        requirements["framework"] = "nextjs"
    elif any(fw in text for fw in ['react', 'vue', 'angular']):
        requirements["framework"] = "react"
    
    # Extract port
    port_match = re.search(r'port\s*:?\s*(\d+)', text)
    if port_match:
        requirements["port"] = int(port_match.group(1))
    
    # Extract domain
    domain_match = re.search(r'domain\s*:?\s*([a-zA-Z0-9.-]+)', text)
    if domain_match:
        requirements["domain"] = domain_match.group(1)
    
    # Extract SSL
    if any(ssl in text for ssl in ['ssl', 'https', 'secure']):
        requirements["ssl"] = True
    
    # Extract autoscaling
    if any(scale in text for scale in ['autoscale', 'auto scale', 'scaling', 'scale up', 'scale down']):
        requirements["autoscale"] = True
    
    # Extract database requirements
    if any(db in text for db in ['database', 'db', 'postgres', 'mysql', 'mongodb', 'redis']):
        requirements["database"] = True
    
    # Extract load balancer requirements
    if any(lb in text for lb in ['load balancer', 'load balancer', 'multiple instances', 'high availability']):
        requirements["load_balancer"] = True
    
    # Extract monitoring requirements
    if any(mon in text for mon in ['monitoring', 'logs', 'metrics', 'alerting', 'observability']):
        requirements["monitoring"] = True
    
    # Extract specific instance types
    if 't2.micro' in text:
        requirements["instance_size"] = "micro"
    elif 't2.small' in text:
        requirements["instance_size"] = "small"
    elif 't2.medium' in text:
        requirements["instance_size"] = "medium"
    elif 't2.large' in text:
        requirements["instance_size"] = "large"
    elif 't3.micro' in text:
        requirements["instance_size"] = "micro"
    elif 't3.small' in text:
        requirements["instance_size"] = "small"
    
    # Extract specific regions with more patterns
    region_patterns = {
        'us-east-1': ['us-east-1', 'virginia', 'n. virginia'],
        'us-west-2': ['us-west-2', 'oregon'],
        'us-west-1': ['us-west-1', 'california', 'n. california'],
        'eu-west-1': ['eu-west-1', 'ireland'],
        'eu-central-1': ['eu-central-1', 'frankfurt'],
        'ap-south-1': ['ap-south-1', 'mumbai'],
        'ap-southeast-1': ['ap-southeast-1', 'singapore']
    }
    
    for region, patterns in region_patterns.items():
        if any(pattern in text for pattern in patterns):
            requirements["region"] = region
            break
    
    return requirements
