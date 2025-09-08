"""
Dockerfile-based application recipe for ECS Fargate deployment.
"""

from typing import Dict, List, Any
import os
import subprocess
import boto3
from pathlib import Path
from .base import Recipe, RecipePlan, get_default_port, get_health_path


class DockerizedRecipe(Recipe):
    """Recipe for Dockerfile-based applications on ECS Fargate."""
    
    def applies(self, spec) -> int:
        """Score how well this recipe fits the Dockerized spec."""
        score = 0
        
        # Check for containerization
        if spec.containerized:
            score += 40
        
        # Check for Dockerfile
        if "Dockerfile" in spec.manifests:
            score += 50
        
        # Check for docker-compose
        if "docker-compose.yml" in spec.manifests:
            score += 30
        
        # Check for container-related files
        if any("docker" in content.lower() for content in spec.manifests.values()):
            score += 20
        
        # Prefer containerized deployments
        if spec.containerized:
            score += 10
        
        return min(score, 100)
    
    def plan(self, spec, infra_plan, patch_result, env_inject, repo_url: str = None) -> RecipePlan:
        """Create deployment plan for Dockerized app."""
        port = get_default_port(spec)
        health_path = get_health_path(spec)
        
        # Build and push Docker image
        image_uri = self._build_and_push_image(spec.app_path, "us-west-2")
        
        # Determine container command and entrypoint
        container_cmd, container_entrypoint = self._extract_container_config(spec)
        
        # Terraform variables for ECS
        tf_vars = {
            "app_name": "dockerized-app",
            "region": "us-west-2",  # Default region, will be overridden by orchestrator
            "port": port,
            "health_path": health_path,
            "image_uri": image_uri,
            "container_cmd": container_cmd,
            "container_entrypoint": container_entrypoint,
            "cpu": "256",
            "memory": "512"
        }
        
        # Smoke checks
        smoke_checks = [
            {"path": "/", "expect": 200},
            {"path": health_path, "expect": 200}
        ]
        
        # Add API endpoint check if likely present
        if any("api" in content.lower() for content in spec.manifests.values()):
            smoke_checks.append({"path": "/api/message", "expect": 200, "contains": "Hello"})
        
        return RecipePlan(
            name="dockerized",
            target="ecs_fargate",
            vars=tf_vars,
            user_data=None,
            container_cmd=container_cmd,
            container_entrypoint=container_entrypoint,
            static_dir=None,
            preflight_notes=[
                "Docker image will be built and pushed to ECR",
                "App will run on ECS Fargate with ALB",
                "Health check endpoint: {}".format(health_path),
                "Environment variables will be injected from SSM Parameter Store"
            ],
            rationale=[
                "Detected Dockerfile or containerized application",
                "ECS Fargate provides managed container hosting",
                "ALB provides load balancing and health checks"
            ],
            smoke_checks=smoke_checks
        )
    
    def _build_and_push_image(self, app_path: str, region: str) -> str:
        """Build Docker image and push to ECR."""
        app_dir = Path(app_path)
        image_name = "arvo-app"
        tag = "latest"
        
        try:
            # Ensure we're in the app directory
            original_cwd = os.getcwd()
            os.chdir(app_dir)
            
            # Build Docker image
            subprocess.run([
                "docker", "build", 
                "-t", f"{image_name}:{tag}",
                "."
            ], check=True)
            
            # Get ECR login token
            ecr_client = boto3.client('ecr', region_name=region)
            token_response = ecr_client.get_authorization_token()
            token = token_response['authorizationData'][0]['authorizationToken']
            endpoint = token_response['authorizationData'][0]['proxyEndpoint']
            
            # Login to ECR
            subprocess.run([
                "docker", "login",
                "--username", "AWS",
                "--password-stdin",
                endpoint
            ], input=token, text=True, check=True)
            
            # Tag image for ECR
            ecr_uri = f"{endpoint.replace('https://', '')}/{image_name}:{tag}"
            subprocess.run([
                "docker", "tag",
                f"{image_name}:{tag}",
                ecr_uri
            ], check=True)
            
            # Push to ECR
            subprocess.run(["docker", "push", ecr_uri], check=True)
            
            return ecr_uri
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Docker build/push failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to build and push Docker image: {e}")
        finally:
            os.chdir(original_cwd)
    
    def _extract_container_config(self, spec) -> tuple:
        """Extract container command and entrypoint from Dockerfile or use defaults."""
        dockerfile_content = spec.manifests.get("Dockerfile", "")
        
        # Parse Dockerfile for CMD and ENTRYPOINT
        container_cmd = None
        container_entrypoint = None
        
        lines = dockerfile_content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('CMD '):
                # Extract CMD arguments
                cmd_args = line[4:].strip()
                if cmd_args.startswith('[') and cmd_args.endswith(']'):
                    # JSON format
                    import json
                    container_cmd = json.loads(cmd_args)
                else:
                    # Shell format
                    container_cmd = cmd_args.split()
            elif line.startswith('ENTRYPOINT '):
                # Extract ENTRYPOINT arguments
                entrypoint_args = line[11:].strip()
                if entrypoint_args.startswith('[') and entrypoint_args.endswith(']'):
                    # JSON format
                    import json
                    container_entrypoint = json.loads(entrypoint_args)
                else:
                    # Shell format
                    container_entrypoint = entrypoint_args.split()
        
        # Use defaults if not found
        if not container_cmd:
            if spec.framework == "flask":
                container_cmd = ["python", "app.py"]
            elif spec.framework == "fastapi":
                container_cmd = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
            elif spec.framework == "django":
                container_cmd = ["python", "manage.py", "runserver", "0.0.0.0:8080"]
            elif spec.framework == "express":
                container_cmd = ["npm", "start"]
            else:
                container_cmd = ["node", "server.js"]
        
        return container_cmd, container_entrypoint
