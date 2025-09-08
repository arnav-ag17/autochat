"""
Base recipe interface and common helpers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class RecipePlan:
    """Complete deployment plan for a specific recipe."""
    name: str                   # "flask", "fastapi", "django", "express", "next_static", "dockerized"
    target: str                 # "ec2" | "ecs_fargate" | "lightsail_containers" | "s3_cf"
    vars: Dict[str, Any]        # vars for TF stack (port, health_path, etc.)
    user_data: Optional[str]    # EC2 only: rendered user_data
    container_cmd: Optional[List[str]]      # ECS: CMD
    container_entrypoint: Optional[List[str]]  # ECS: ENTRYPOINT
    static_dir: Optional[str]   # for S3+CF uploads
    preflight_notes: List[str]  # human hints (non-blocking)
    rationale: List[str]        # why this recipe
    smoke_checks: List[Dict]    # e.g., [{"path":"/","expect":200},{"path":"/api/message","expect":200,"contains":"Hello"}]


class Recipe(ABC):
    """Abstract base class for deployment recipes."""
    
    @abstractmethod
    def applies(self, spec) -> int:
        """
        Return score (0..100) for how well this recipe fits the spec.
        
        Args:
            spec: DeploymentSpec from analyzer
            
        Returns:
            Score from 0-100, where 100 is perfect match
        """
        pass
    
    @abstractmethod
    def plan(self, spec, infra_plan, patch_result, env_inject, repo_url: str = None) -> RecipePlan:
        """
        Return a complete plan for TF inputs & runtime execution.
        
        Args:
            spec: DeploymentSpec from analyzer
            infra_plan: InfraPlan from selector
            patch_result: Result from patcher (Stage 5)
            env_inject: Environment injection result (Stage 6)
            
        Returns:
            Complete RecipePlan for deployment
        """
        pass


def get_default_port(spec) -> int:
    """Get default port from spec or framework defaults."""
    if spec.port:
        return spec.port
    
    # Framework-specific defaults
    if spec.framework in ["flask", "fastapi"]:
        return 5000 if spec.framework == "flask" else 8000
    elif spec.framework in ["django"]:
        return 8000
    elif spec.framework in ["express", "nextjs"]:
        return 3000
    else:
        return 8080


def get_health_path(spec) -> str:
    """Get health check path from spec or defaults."""
    if spec.health_path:
        return spec.health_path
    
    # Framework-specific defaults
    if spec.framework in ["flask", "fastapi"]:
        return "/health"
    elif spec.framework in ["django"]:
        return "/admin/login"  # Django admin is a good health check
    elif spec.framework in ["express", "nextjs"]:
        return "/"
    else:
        return "/"


def create_user_data_template() -> str:
    """Create base user_data template for EC2 deployments."""
    return """#!/bin/bash
set -e

# Update system
yum update -y

# Install git (required for repo cloning)
yum install -y git

# Create app directory
mkdir -p /opt/arvo-app
cd /opt/arvo-app

# Clone repository
git clone {{REPO_URL}} .

# Source environment variables
if [ -f /etc/default/arvo-app ]; then
    source /etc/default/arvo-app
fi

# Set default port if not provided
export PORT=${PORT:-{{DEFAULT_PORT}}}

# Install and start application
{{INSTALL_COMMANDS}}

# Navigate to app directory if it exists
if [ -d "app" ]; then
    cd app
fi

# Fix Flask app configuration for deployment
if [ -f "app.py" ]; then
    # Create a deployment version of app.py that binds to 0.0.0.0
    sed -i 's/app.run(host="127.0.0.1", port=5000)/app.run(host="0.0.0.0", port=${PORT:-8080})/g' app.py
    sed -i 's/app.run(host="127.0.0.1")/app.run(host="0.0.0.0", port=${PORT:-8080})/g' app.py
    sed -i 's/app.run(port=5000)/app.run(host="0.0.0.0", port=${PORT:-8080})/g' app.py
    sed -i 's/app.run()/app.run(host="0.0.0.0", port=${PORT:-8080})/g' app.py
fi

# Create systemd service
cat > /etc/systemd/system/arvo-app.service << 'EOF'
[Unit]
Description=Arvo Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/arvo-app/app
Environment=PORT=$PORT
ExecStart={{START_COMMAND}}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable arvo-app
systemctl start arvo-app

# Wait for service to be ready
sleep 10
systemctl status arvo-app
"""


def create_python_install_commands(spec, use_venv: bool = True) -> str:
    """Create Python installation commands."""
    commands = []
    
    if use_venv:
        commands.append("python3 -m venv venv")
        commands.append("source venv/bin/activate")
    
    # Install dependencies
    if spec.manifests.get("requirements.txt"):
        commands.append("pip install -r requirements.txt")
    elif spec.manifests.get("pyproject.toml"):
        commands.append("pip install -e .")
    else:
        commands.append("pip install {{FRAMEWORK_PACKAGE}}")
    
    return " && ".join(commands)


def create_node_install_commands(spec) -> str:
    """Create Node.js installation commands."""
    commands = []
    
    # Install Node.js (using NodeSource repository for latest LTS)
    commands.extend([
        "curl -fsSL https://rpm.nodesource.com/setup_lts.x | bash -",
        "yum install -y nodejs"
    ])
    
    # Install dependencies
    if spec.manifests.get("package-lock.json"):
        commands.append("npm ci")
    elif spec.manifests.get("yarn.lock"):
        commands.append("yarn install")
    else:
        commands.append("npm install")
    
    return " && ".join(commands)


def create_start_command(spec, framework: str) -> str:
    """Create start command based on framework and spec."""
    if spec.start_command:
        return spec.start_command
    
    # Framework-specific start commands
    if framework == "flask":
        return "/opt/arvo-app/venv/bin/python app.py"
    elif framework == "fastapi":
        return "uvicorn main:app --host 0.0.0.0 --port $PORT"
    elif framework == "django":
        return "python manage.py runserver 0.0.0.0:$PORT"
    elif framework == "express":
        return "npm start"
    else:
        return "node server.js"
