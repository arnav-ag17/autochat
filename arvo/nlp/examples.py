"""
Few-shot examples for LLM calls.
"""

from typing import List, Dict, Any


def get_examples() -> List[Dict[str, Any]]:
    """Get few-shot examples for LLM extraction."""
    return [
        {
            "input": "Deploy this Django app on AWS with a small VM in Oregon, add a custom domain api.foo.com and HTTPS; auto-destroy in 24h.",
            "output": {
                "cloud": "aws",
                "infra": "ec2",
                "region": "us-west-2",
                "instance_size": "small",
                "domain": "api.foo.com",
                "ssl": True,
                "ttl_hours": 24,
                "notes": ["Django app detected", "Oregon mapped to us-west-2", "HTTPS enabled for custom domain"],
                "confidence": 0.9
            }
        },
        {
            "input": "Serverless Python on AWS us-east-1, no DB, 24h TTL",
            "output": {
                "cloud": "aws",
                "infra": "lambda",
                "region": "us-east-1",
                "db": {"engine": "none"},
                "ttl_hours": 24,
                "notes": ["Serverless deployment", "No database required"],
                "confidence": 0.8
            }
        },
        {
            "input": "Containerize on AWS, region Oregon, autoscale 1..3",
            "output": {
                "cloud": "aws",
                "infra": "ecs_fargate",
                "region": "us-west-2",
                "containerized": True,
                "autoscale": True,
                "min_instances": 1,
                "max_instances": 3,
                "notes": ["Containerized deployment", "Oregon mapped to us-west-2", "Autoscaling enabled"],
                "confidence": 0.85
            }
        },
        {
            "input": "Static Next.js site to CDN with https",
            "output": {
                "infra": "s3_cf",
                "ssl": True,
                "notes": ["Static site deployment", "CDN with HTTPS"],
                "confidence": 0.9
            }
        },
        {
            "input": "Deploy Flask app on t3.medium in us-west-2 with postgres database",
            "output": {
                "infra": "ec2",
                "region": "us-west-2",
                "instance_type": "t3.medium",
                "instance_size": "medium",
                "db": {"engine": "postgres"},
                "notes": ["Flask app detected", "Specific instance type requested"],
                "confidence": 0.95
            }
        },
        {
            "input": "Deploy serverless on EC2",
            "output": {
                "infra": None,
                "notes": ["Conflicting infrastructure requests: serverless vs EC2", "Leaving infrastructure selection to system"],
                "confidence": 0.3
            }
        },
        {
            "input": "Deploy my app with a large VM and custom domain example.com",
            "output": {
                "infra": "ec2",
                "instance_size": "large",
                "domain": "example.com",
                "notes": ["Large VM requested", "Custom domain specified"],
                "confidence": 0.7
            }
        },
        {
            "input": "Deploy containerized app with autoscaling from 2 to 10 instances",
            "output": {
                "infra": "ecs_fargate",
                "containerized": True,
                "autoscale": True,
                "min_instances": 2,
                "max_instances": 10,
                "notes": ["Containerized deployment", "Autoscaling with specific range"],
                "confidence": 0.9
            }
        },
        {
            "input": "Deploy on AWS with micro instance and no database",
            "output": {
                "cloud": "aws",
                "infra": "ec2",
                "instance_size": "micro",
                "db": {"engine": "none"},
                "notes": ["Micro instance for cost efficiency", "No database required"],
                "confidence": 0.8
            }
        },
        {
            "input": "Deploy static website with CloudFront and SSL",
            "output": {
                "infra": "s3_cf",
                "ssl": True,
                "notes": ["Static website deployment", "CloudFront CDN with SSL"],
                "confidence": 0.9
            }
        }
    ]


def get_examples_by_type(example_type: str) -> List[Dict[str, Any]]:
    """Get examples filtered by type."""
    all_examples = get_examples()
    
    if example_type == "conflict":
        return [ex for ex in all_examples if "conflict" in ex["output"].get("notes", [])]
    elif example_type == "simple":
        return [ex for ex in all_examples if ex["output"].get("confidence", 0) > 0.8]
    elif example_type == "complex":
        return [ex for ex in all_examples if len(ex["output"].get("notes", [])) > 2]
    else:
        return all_examples


def get_example_inputs() -> List[str]:
    """Get just the input texts from examples."""
    return [ex["input"] for ex in get_examples()]


def get_example_outputs() -> List[Dict[str, Any]]:
    """Get just the output objects from examples."""
    return [ex["output"] for ex in get_examples()]


def find_similar_example(instructions: str) -> Dict[str, Any]:
    """Find the most similar example to given instructions."""
    examples = get_examples()
    instructions_lower = instructions.lower()
    
    best_match = None
    best_score = 0
    
    for example in examples:
        input_lower = example["input"].lower()
        
        # Simple keyword matching
        score = 0
        keywords = ["aws", "ec2", "lambda", "container", "static", "django", "flask", "serverless"]
        for keyword in keywords:
            if keyword in instructions_lower and keyword in input_lower:
                score += 1
        
        if score > best_score:
            best_score = score
            best_match = example
    
    return best_match or examples[0]  # Return first example as fallback
