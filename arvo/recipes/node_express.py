"""
Node.js/Express application recipe for EC2 deployment.
"""

from typing import Dict, List, Any
from .base import Recipe, RecipePlan, get_default_port, get_health_path, create_user_data_template, create_node_install_commands, create_start_command


class NodeExpressRecipe(Recipe):
    """Recipe for Node.js/Express applications on EC2."""
    
    def applies(self, spec) -> int:
        """Score how well this recipe fits the Node.js/Express spec."""
        score = 0
        
        # Check runtime
        if spec.runtime == "node":
            score += 30
        elif spec.runtime == "unknown":
            score += 10
        
        # Check framework
        if spec.framework == "express":
            score += 50
        elif spec.framework is None:
            # Check for Express in manifests
            if "express" in spec.manifests.get("package.json", "").lower():
                score += 40
        
        # Check for package.json
        if "package.json" in spec.manifests:
            score += 20
        
        # Check for Express imports in code
        if any("require('express')" in content or "import express" in content 
               for content in spec.manifests.values()):
            score += 20
        
        # Prefer non-containerized
        if not spec.containerized:
            score += 10
        
        return min(score, 100)
    
    def plan(self, spec, infra_plan, patch_result, env_inject, repo_url: str = None) -> RecipePlan:
        """Create deployment plan for Node.js/Express app."""
        port = get_default_port(spec)
        health_path = get_health_path(spec)
        
        # Create user_data template
        user_data_template = create_user_data_template()
        install_commands = create_node_install_commands(spec)
        start_command = create_start_command(spec, "express")
        
        # Replace template variables
        user_data = user_data_template.replace("{{REPO_URL}}", repo_url or spec.app_path)
        user_data = user_data.replace("{{DEFAULT_PORT}}", str(port))
        user_data = user_data.replace("{{INSTALL_COMMANDS}}", install_commands)
        user_data = user_data.replace("{{START_COMMAND}}", start_command)
        
        # Terraform variables
        tf_vars = {
            "app_name": "express-app",
            "region": "us-west-2",  # Default region, will be overridden by orchestrator
            "port": port,
            "health_path": health_path
        }
        
        # Smoke checks
        smoke_checks = [
            {"path": "/", "expect": 200},
            {"path": "/api/message", "expect": 200, "contains": "Hello"}
        ]
        
        # Add health endpoint check if likely present
        if any("health" in content.lower() for content in spec.manifests.values()):
            smoke_checks.append({"path": "/health", "expect": 200})
        
        return RecipePlan(
            name="express",
            target="ec2",
            vars=tf_vars,
            user_data=user_data,
            container_cmd=None,
            container_entrypoint=None,
            static_dir=None,
            preflight_notes=[
                "Node.js/Express app will be served on port {}".format(port),
                "Health check endpoint: {}".format(health_path),
                "Node.js LTS will be installed via NodeSource repository",
                "Environment variables will be injected from SSM Parameter Store"
            ],
            rationale=[
                "Detected Express framework in package.json or code",
                "Non-containerized Node.js app, defaulting to EC2",
                "Will use npm start or node server.js for process management"
            ],
            smoke_checks=smoke_checks
        )
