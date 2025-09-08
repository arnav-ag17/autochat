"""
LLM-powered Terraform generator that uses comprehensive analysis.
"""

import json
from typing import Dict, Any, List

class LLMTerraformGenerator:
    """Generate Terraform configuration based on LLM analysis."""
    
    def generate_terraform_config(self, requirements: Dict[str, Any], analysis: Dict[str, Any], region: str, repo_url: str) -> Dict[str, str]:
        """
        Generate Terraform configuration files based on LLM analysis.
        
        Args:
            requirements: LLM-extracted requirements
            analysis: LLM repository analysis
            region: AWS region
            repo_url: Repository URL
            
        Returns:
            Dictionary with Terraform file contents
        """
        
        # Extract key information from LLM analysis
        infra_req = requirements.get("infrastructure_requirements", {})
        app_req = requirements.get("application_requirements", {})
        db_req = requirements.get("database_requirements", {})
        security_req = requirements.get("security_requirements", {})
        monitoring_req = requirements.get("monitoring_logging", {})
        networking_req = requirements.get("networking", {})
        
        # Repository analysis
        app_type = analysis.get("Application Classification", {}).get("application_type", "web_app")
        framework = analysis.get("Application Classification", {}).get("framework") or app_req.get("framework", "flask")
        runtime = analysis.get("Application Classification", {}).get("primary_language") or app_req.get("runtime", "python")
        
        # Determine infrastructure components needed
        needs_database = db_req.get("database_type") != "none"
        needs_load_balancer = networking_req.get("load_balancer", False)
        needs_vpc = security_req.get("vpc_required", False)
        needs_ssl = security_req.get("ssl_enabled", False)
        needs_monitoring = monitoring_req.get("monitoring_enabled", False)
        needs_auto_scaling = infra_req.get("auto_scaling", False)
        
        # Generate main.tf
        main_tf = self._generate_main_tf(
            infra_req, app_req, db_req, security_req, networking_req, 
            monitoring_req, needs_database, needs_load_balancer, needs_vpc, 
            needs_ssl, needs_monitoring, needs_auto_scaling, region, repo_url
        )
        
        # Generate variables.tf
        variables_tf = self._generate_variables_tf(infra_req, app_req, db_req)
        
        # Generate outputs.tf
        outputs_tf = self._generate_outputs_tf(needs_load_balancer, needs_ssl)
        
        return {
            "main.tf": main_tf,
            "variables.tf": variables_tf,
            "outputs.tf": outputs_tf
        }
    
    def _generate_main_tf(self, infra_req: Dict, app_req: Dict, db_req: Dict, 
                         security_req: Dict, networking_req: Dict, monitoring_req: Dict,
                         needs_database: bool, needs_load_balancer: bool, needs_vpc: bool,
                         needs_ssl: bool, needs_monitoring: bool, needs_auto_scaling: bool,
                         region: str, repo_url: str) -> str:
        """Generate main.tf based on LLM requirements."""
        
        instance_type = infra_req.get("instance_type", "t2.micro")
        instance_count = infra_req.get("instance_count", 1)
        port = app_req.get("port", 5000)
        
        # Start building Terraform configuration
        terraform_config = f"""
terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{region}"
}}

# Data sources
data "aws_availability_zones" "available" {{
  state = "available"
}}

data "aws_ami" "amazon_linux" {{
  most_recent = true
  owners      = ["amazon"]
  
  filter {{
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }}
}}
"""
        
        # VPC and networking if required
        if needs_vpc:
            terraform_config += f"""
# VPC
resource "aws_vpc" "main" {{
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {{
    Name = "llm-deploy-vpc"
  }}
}}

# Internet Gateway
resource "aws_internet_gateway" "main" {{
  vpc_id = aws_vpc.main.id
  
  tags = {{
    Name = "llm-deploy-igw"
  }}
}}

# Public Subnets
resource "aws_subnet" "public" {{
  count = 2
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${{count.index + 1}}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {{
    Name = "llm-deploy-public-subnet-${{count.index + 1}}"
  }}
}}

# Route Table
resource "aws_route_table" "public" {{
  vpc_id = aws_vpc.main.id
  
  route {{
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }}
  
  tags = {{
    Name = "llm-deploy-public-rt"
  }}
}}

resource "aws_route_table_association" "public" {{
  count = 2
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}}
"""
        
        # Security Group
        terraform_config += f"""
# Security Group
resource "aws_security_group" "app" {{
  name_prefix = "llm-deploy-"
  description = "Security group for LLM-deployed application"
  {f'vpc_id = aws_vpc.main.id' if needs_vpc else ''}
  
  # Application port
  ingress {{
    from_port   = {port}
    to_port     = {port}
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Application port"
  }}
  
  # SSH access
  ingress {{
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }}
  
  # HTTPS if SSL enabled
  {f'''
  ingress {{
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }}''' if needs_ssl else ''}
  
  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }}
  
  tags = {{
    Name = "llm-deploy-sg"
  }}
}}
"""
        
        # Database if required
        if needs_database:
            db_type = db_req.get("database_type", "postgresql")
            terraform_config += f"""
# Database
resource "aws_db_instance" "main" {{
  identifier = "llm-deploy-db"
  
  engine         = "{db_type}"
  engine_version = "13.7"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  storage_type   = "gp2"
  storage_encrypted = {str(security_req.get("encryption_at_rest", False)).lower()}
  
  db_name  = "appdb"
  username = "dbuser"
  password = "dbpassword123"  # In production, use AWS Secrets Manager
  
  vpc_security_group_ids = [aws_security_group.db.id]
  {f'db_subnet_group_name = aws_db_subnet_group.main.name' if needs_vpc else ''}
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  
  tags = {{
    Name = "llm-deploy-db"
  }}
}}

# Database Security Group
resource "aws_security_group" "db" {{
  name_prefix = "llm-deploy-db-"
  description = "Security group for database"
  {f'vpc_id = aws_vpc.main.id' if needs_vpc else ''}
  
  ingress {{
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
    description     = "PostgreSQL access from app"
  }}
  
  tags = {{
    Name = "llm-deploy-db-sg"
  }}
}}
"""
            
            if needs_vpc:
                terraform_config += """
# Database Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "llm-deploy-db-subnet-group"
  subnet_ids = aws_subnet.public[*].id
  
  tags = {
    Name = "llm-deploy-db-subnet-group"
  }
}
"""
        
        # Load Balancer if required
        if needs_load_balancer:
            terraform_config += f"""
# Application Load Balancer
resource "aws_lb" "main" {{
  name               = "llm-deploy-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  {f'subnets = aws_subnet.public[*].id' if needs_vpc else 'subnets = data.aws_subnets.default.ids'}
  
  enable_deletion_protection = false
  
  tags = {{
    Name = "llm-deploy-alb"
  }}
}}

# ALB Security Group
resource "aws_security_group" "alb" {{
  name_prefix = "llm-deploy-alb-"
  description = "Security group for ALB"
  {f'vpc_id = aws_vpc.main.id' if needs_vpc else ''}
  
  ingress {{
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }}
  
  {f'''
  ingress {{
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }}''' if needs_ssl else ''}
  
  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }}
  
  tags = {{
    Name = "llm-deploy-alb-sg"
  }}
}}

# Target Group
resource "aws_lb_target_group" "app" {{
  name     = "llm-deploy-tg"
  port     = {port}
  protocol = "HTTP"
  {f'vpc_id = aws_vpc.main.id' if needs_vpc else 'vpc_id = data.aws_vpc.default.id'}
  
  health_check {{
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }}
  
  tags = {{
    Name = "llm-deploy-tg"
  }}
}}

# ALB Listener
resource "aws_lb_listener" "app" {{
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {{
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }}
}}
"""
        
        # Auto Scaling Group if required
        if needs_auto_scaling:
            auto_scaling = infra_req.get("auto_scaling", {})
            min_size = auto_scaling.get("min_instances", 1)
            max_size = auto_scaling.get("max_instances", 3)
            
            terraform_config += f"""
# Launch Template
resource "aws_launch_template" "app" {{
  name_prefix   = "llm-deploy-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = "{instance_type}"
  
  vpc_security_group_ids = [aws_security_group.app.id]
  
  user_data = base64encode(templatefile("${{path.module}}/user_data.sh", {{
    repo_url = "{repo_url}"
    app_port = {port}
  }}))
  
  tag_specifications {{
    resource_type = "instance"
    tags = {{
      Name = "llm-deploy-instance"
    }}
  }}
}}

# Auto Scaling Group
resource "aws_autoscaling_group" "app" {{
  name                = "llm-deploy-asg"
  vpc_zone_identifier = {f'aws_subnet.public[*].id' if needs_vpc else 'data.aws_subnets.default.ids'}
  target_group_arns   = {f'[aws_lb_target_group.app.arn]' if needs_load_balancer else '[]'}
  health_check_type   = {f'"ELB"' if needs_load_balancer else '"EC2"'}
  
  min_size         = {min_size}
  max_size         = {max_size}
  desired_capacity = {min_size}
  
  launch_template {{
    id      = aws_launch_template.app.id
    version = "$Latest"
  }}
  
  tag {{
    key                 = "Name"
    value               = "llm-deploy-asg"
    propagate_at_launch = false
  }}
}}

# Auto Scaling Policy
resource "aws_autoscaling_policy" "scale_up" {{
  name                   = "llm-deploy-scale-up"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.app.name
}}

resource "aws_autoscaling_policy" "scale_down" {{
  name                   = "llm-deploy-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.app.name
}}
"""
        else:
            # Single instance if no auto-scaling
            terraform_config += f"""
# EC2 Instance
resource "aws_instance" "app" {{
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "{instance_type}"
  
  vpc_security_group_ids = [aws_security_group.app.id]
  {f'subnet_id = aws_subnet.public[0].id' if needs_vpc else ''}
  
  user_data = base64encode(templatefile("${{path.module}}/user_data.sh", {{
    repo_url = "{repo_url}"
    app_port = {port}
  }}))
  
  tags = {{
    Name = "llm-deploy-instance"
  }}
}}

# Elastic IP
resource "aws_eip" "app" {{
  instance = aws_instance.app.id
  domain   = "vpc"
  
  tags = {{
    Name = "llm-deploy-eip"
  }}
}}
"""
        
        # CloudWatch monitoring if required
        if needs_monitoring:
            terraform_config += """
# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/ec2/llm-deploy"
  retention_in_days = 30
  
  tags = {
    Name = "llm-deploy-logs"
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "llm-deploy-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", "i-1234567890abcdef0"],
            [".", "NetworkIn", ".", "."],
            [".", "NetworkOut", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-west-2"
          title   = "EC2 Metrics"
          period  = 300
        }
      }
    ]
  })
}
"""
        
        # Data sources for default VPC if not using custom VPC
        if not needs_vpc:
            terraform_config += """
# Default VPC data sources
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
"""
        
        return terraform_config
    
    def _generate_variables_tf(self, infra_req: Dict, app_req: Dict, db_req: Dict) -> str:
        """Generate variables.tf."""
        return """
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "app_port" {
  description = "Application port"
  type        = number
  default     = 5000
}

variable "repo_url" {
  description = "Repository URL"
  type        = string
}
"""
    
    def _generate_outputs_tf(self, needs_load_balancer: bool, needs_ssl: bool) -> str:
        """Generate outputs.tf."""
        if needs_load_balancer:
            return """
output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "application_url" {
  description = "Application URL"
  value       = "http://${aws_lb.main.dns_name}"
}
"""
        else:
            return """
output "public_ip" {
  description = "Public IP address of the instance"
  value       = aws_eip.app.public_ip
}

output "application_url" {
  description = "Application URL"
  value       = "http://${aws_eip.app.public_ip}:5000"
}
"""


def test_terraform_generator():
    """Test the Terraform generator."""
    print("🧪 Testing LLM Terraform Generator")
    print("=" * 50)
    
    # Sample LLM requirements
    requirements = {
        "infrastructure_requirements": {
            "cloud_provider": "aws",
            "infrastructure_type": "vm",
            "region": "us-east-1",
            "instance_type": "t2.medium",
            "instance_count": 1,
            "auto_scaling": {"enabled": True, "min_instances": 2, "max_instances": 5}
        },
        "application_requirements": {
            "framework": "flask",
            "runtime": "python",
            "port": 5000
        },
        "database_requirements": {
            "database_type": "postgresql"
        },
        "security_requirements": {
            "ssl_enabled": True,
            "vpc_required": True
        },
        "networking": {
            "load_balancer": True
        },
        "monitoring_logging": {
            "monitoring_enabled": True
        }
    }
    
    # Sample repository analysis
    analysis = {
        "Application Classification": {
            "application_type": "web_app",
            "framework": "flask",
            "primary_language": "python"
        }
    }
    
    generator = LLMTerraformGenerator()
    terraform_files = generator.generate_terraform_config(
        requirements, analysis, "us-west-2", "https://github.com/Arvo-AI/hello_world"
    )
    
    print("Generated Terraform files:")
    for filename, content in terraform_files.items():
        print(f"\n📄 {filename} ({len(content)} characters)")
        print("=" * 30)
        print(content[:500] + "..." if len(content) > 500 else content)
    
    return terraform_files


if __name__ == "__main__":
    test_terraform_generator()
