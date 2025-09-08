"""
FastAPI application recipe for EC2 deployment.
"""

from typing import Dict, List, Any
from .base import Recipe, RecipePlan, get_default_port, get_health_path, create_user_data_template, create_python_install_commands, create_start_command


class FastAPIRecipe(Recipe):
    """Recipe for FastAPI applications on EC2."""
    
    def applies(self, spec) -> int:
        """Score how well this recipe fits the FastAPI spec."""
        score = 0
        
        # Check runtime
        if spec.runtime == "python":
            score += 30
        elif spec.runtime == "unknown":
            score += 10
        
        # Check framework
        if spec.framework == "fastapi":
            score += 50
        elif spec.framework is None:
            # Check for FastAPI in manifests
            if "fastapi" in spec.manifests.get("requirements.txt", "").lower():
                score += 40
            elif "fastapi" in spec.manifests.get("pyproject.toml", "").lower():
                score += 40
        
        # Check for FastAPI imports in code
        if any("from fastapi import" in content.lower() or "fastapi(" in content.lower() 
               for content in spec.manifests.values()):
            score += 20
        
        # Prefer non-containerized
        if not spec.containerized:
            score += 10
        
        return min(score, 100)
    
    def plan(self, spec, infra_plan, patch_result, env_inject, repo_url: str = None) -> RecipePlan:
        """Create deployment plan for FastAPI app."""
        port = get_default_port(spec)
        health_path = get_health_path(spec)
        
        # Create user_data template
        user_data_template = create_user_data_template()
        install_commands = create_python_install_commands(spec)
        start_command = create_start_command(spec, "fastapi")
        
        # Replace template variables
        user_data = user_data_template.replace("{{REPO_URL}}", repo_url or spec.app_path)
        user_data = user_data.replace("{{DEFAULT_PORT}}", str(port))
        user_data = user_data.replace("{{INSTALL_COMMANDS}}", install_commands)
        user_data = user_data.replace("{{FRAMEWORK_PACKAGE}}", "fastapi uvicorn")
        user_data = user_data.replace("{{START_COMMAND}}", start_command)
        
        # Terraform variables
        tf_vars = {
            "app_name": "fastapi-app",
            "region": "us-west-2",  # Default region, will be overridden by orchestrator
            "port": port,
            "health_path": health_path
        }
        
        # Smoke checks
        smoke_checks = [
            {"path": "/", "expect": 200},
            {"path": "/health", "expect": 200, "contains": "ok"},
            {"path": "/docs", "expect": 200}  # FastAPI auto-generated docs
        ]
        
        # Add API endpoint check if likely present
        if any("api" in content.lower() for content in spec.manifests.values()):
            smoke_checks.append({"path": "/api/message", "expect": 200, "contains": "Hello"})
        
        return RecipePlan(
            name="fastapi",
            target="ec2",
            vars=tf_vars,
            user_data=user_data,
            container_cmd=None,
            container_entrypoint=None,
            static_dir=None,
            preflight_notes=[
                "FastAPI app will be served on port {} with uvicorn".format(port),
                "Health check endpoint: {}".format(health_path),
                "API documentation available at /docs",
                "Environment variables will be injected from SSM Parameter Store"
            ],
            rationale=[
                "Detected FastAPI framework in requirements.txt or code",
                "Non-containerized Python app, defaulting to EC2",
                "Will use uvicorn ASGI server for production-ready deployment"
            ],
            smoke_checks=smoke_checks
        )
