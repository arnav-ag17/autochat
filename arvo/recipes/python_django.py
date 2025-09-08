"""
Django application recipe for EC2 deployment.
"""

from typing import Dict, List, Any
from .base import Recipe, RecipePlan, get_default_port, get_health_path, create_user_data_template, create_python_install_commands, create_start_command


class DjangoRecipe(Recipe):
    """Recipe for Django applications on EC2."""
    
    def applies(self, spec) -> int:
        """Score how well this recipe fits the Django spec."""
        score = 0
        
        # Check runtime
        if spec.runtime == "python":
            score += 30
        elif spec.runtime == "unknown":
            score += 10
        
        # Check framework
        if spec.framework == "django":
            score += 50
        elif spec.framework is None:
            # Check for Django in manifests
            if "django" in spec.manifests.get("requirements.txt", "").lower():
                score += 40
            elif "django" in spec.manifests.get("pyproject.toml", "").lower():
                score += 40
        
        # Check for Django-specific files
        if "manage.py" in spec.manifests:
            score += 30
        
        # Check for Django imports in code
        if any("from django" in content.lower() or "django" in content.lower() 
               for content in spec.manifests.values()):
            score += 20
        
        # Prefer non-containerized
        if not spec.containerized:
            score += 10
        
        return min(score, 100)
    
    def plan(self, spec, infra_plan, patch_result, env_inject, repo_url: str = None) -> RecipePlan:
        """Create deployment plan for Django app."""
        port = get_default_port(spec)
        health_path = get_health_path(spec)
        
        # Create user_data template with Django-specific setup
        user_data_template = create_user_data_template()
        install_commands = create_python_install_commands(spec)
        start_command = create_start_command(spec, "django")
        
        # Add Django-specific commands
        django_commands = [
            "python manage.py migrate --noinput",
            "python manage.py collectstatic --noinput || echo 'Warning: collectstatic failed, continuing...'"
        ]
        
        # Replace template variables
        user_data = user_data_template.replace("{{REPO_URL}}", repo_url or spec.app_path)
        user_data = user_data.replace("{{DEFAULT_PORT}}", str(port))
        user_data = user_data.replace("{{INSTALL_COMMANDS}}", install_commands + " && " + " && ".join(django_commands))
        user_data = user_data.replace("{{FRAMEWORK_PACKAGE}}", "django")
        user_data = user_data.replace("{{START_COMMAND}}", start_command)
        
        # Terraform variables
        tf_vars = {
            "app_name": "django-app",
            "region": "us-west-2",  # Default region, will be overridden by orchestrator
            "port": port,
            "health_path": health_path
        }
        
        # Smoke checks
        smoke_checks = [
            {"path": "/", "expect": 200},
            {"path": "/admin/login", "expect": [200, 302]}  # Django admin login
        ]
        
        # Add API endpoint check if likely present
        if any("api" in content.lower() or "rest_framework" in content.lower() 
               for content in spec.manifests.values()):
            smoke_checks.append({"path": "/api/", "expect": 200})
        
        # Preflight notes
        preflight_notes = [
            "Django app will be served on port {}".format(port),
            "Health check endpoint: {}".format(health_path),
            "Database migrations will be run automatically",
            "Static files will be collected automatically",
            "Environment variables will be injected from SSM Parameter Store"
        ]
        
        # Add database warning if needed
        if spec.db_required:
            preflight_notes.append("⚠️  Database required - ensure DATABASE_URL is set in environment")
        
        return RecipePlan(
            name="django",
            target="ec2",
            vars=tf_vars,
            user_data=user_data,
            container_cmd=None,
            container_entrypoint=None,
            static_dir=None,
            preflight_notes=preflight_notes,
            rationale=[
                "Detected Django framework with manage.py",
                "Non-containerized Python app, defaulting to EC2",
                "Will run migrations and collect static files automatically",
                "Uses Django's built-in development server (consider gunicorn for production)"
            ],
            smoke_checks=smoke_checks
        )
