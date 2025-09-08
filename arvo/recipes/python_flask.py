"""
Flask application recipe for EC2 deployment.
"""

from typing import Dict, List, Any
from .base import Recipe, RecipePlan, get_default_port, get_health_path, create_user_data_template, create_python_install_commands, create_start_command


class FlaskRecipe(Recipe):
    """Recipe for Flask applications on EC2."""
    
    def applies(self, spec) -> int:
        """Score how well this recipe fits the Flask spec."""
        score = 0
        
        # Check runtime
        if spec.runtime == "python":
            score += 30
        elif spec.runtime == "unknown":
            score += 10
        
        # Check framework
        if spec.framework == "flask":
            score += 50
        elif spec.framework is None:
            # Check for Flask in manifests
            if "flask" in spec.manifests.get("requirements.txt", "").lower():
                score += 40
            elif "Flask" in spec.manifests.get("pyproject.toml", ""):
                score += 40
        
        # Check for Flask imports in code
        if any("from flask import" in content.lower() or "flask(" in content.lower() 
               for content in spec.manifests.values()):
            score += 20
        
        # Prefer non-containerized
        if not spec.containerized:
            score += 10
        
        return min(score, 100)
    
    def plan(self, spec, infra_plan, patch_result, env_inject, repo_url: str = None) -> RecipePlan:
        """Create deployment plan for Flask app."""
        port = get_default_port(spec)
        health_path = get_health_path(spec)
        
        # Create user_data template
        user_data_template = create_user_data_template()
        install_commands = create_python_install_commands(spec)
        start_command = create_start_command(spec, "flask")
        
        # Replace template variables
        user_data = user_data_template.replace("{{REPO_URL}}", repo_url or spec.app_path)
        user_data = user_data.replace("{{DEFAULT_PORT}}", str(port))
        user_data = user_data.replace("{{INSTALL_COMMANDS}}", install_commands)
        user_data = user_data.replace("{{FRAMEWORK_PACKAGE}}", "flask")
        user_data = user_data.replace("{{START_COMMAND}}", start_command)
        
        # Terraform variables
        tf_vars = {
            "app_name": "flask-app",
            "region": "us-west-2",  # Default region, will be overridden by orchestrator
            "port": port,
            "health_path": health_path
        }
        
        # Smoke checks
        smoke_checks = [
            {"path": "/", "expect": 200},
            {"path": "/health", "expect": 200, "contains": "ok"}
        ]
        
        # Add API endpoint check if likely present
        if any("api" in content.lower() for content in spec.manifests.values()):
            smoke_checks.append({"path": "/api/message", "expect": 200, "contains": "Hello"})
        
        return RecipePlan(
            name="flask",
            target="ec2",
            vars=tf_vars,
            user_data=user_data,
            container_cmd=None,
            container_entrypoint=None,
            static_dir=None,
            preflight_notes=[
                "Flask app will be served on port {}".format(port),
                "Health check endpoint: {}".format(health_path),
                "Environment variables will be injected from SSM Parameter Store"
            ],
            rationale=[
                "Detected Flask framework in requirements.txt or code",
                "Non-containerized Python app, defaulting to EC2",
                "Will use systemd service for process management"
            ],
            smoke_checks=smoke_checks
        )
