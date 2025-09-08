"""
Support for different infrastructure types: VM, Serverless, Kubernetes
"""

from typing import Dict, Any, List
from .llm_terraform_generator import LLMTerraformGenerator


class ServerlessTerraformGenerator(LLMTerraformGenerator):
    """Generate Terraform for serverless infrastructure (AWS Lambda, API Gateway)."""
    
    def generate_terraform_config(self, requirements: Dict[str, Any], analysis: Dict[str, Any], region: str, repo_url: str) -> Dict[str, str]:
        """Generate serverless Terraform configuration."""
        
        app_req = requirements.get("application_requirements", {})
        framework = app_req.get("framework", "flask")
        runtime = app_req.get("runtime", "python")
        
        # Generate main.tf for serverless
        main_tf = f"""
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

# Lambda function
resource "aws_lambda_function" "app" {{
  filename         = "app.zip"
  function_name    = "llm-deploy-app"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30
  
  environment {{
    variables = {{
      REPO_URL = "{repo_url}"
    }}
  }}
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {{
  name = "llm-deploy-lambda-role"
  
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {{
          Service = "lambda.amazonaws.com"
        }}
      }}
    ]
  }})
}}

resource "aws_iam_role_policy_attachment" "lambda_logs" {{
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {{
  name              = "/aws/lambda/llm-deploy-app"
  retention_in_days = 14
}}

# API Gateway
resource "aws_api_gateway_rest_api" "app" {{
  name        = "llm-deploy-api"
  description = "API Gateway for LLM deployed application"
}}

resource "aws_api_gateway_resource" "proxy" {{
  rest_api_id = aws_api_gateway_rest_api.app.id
  parent_id   = aws_api_gateway_rest_api.app.root_resource_id
  path_part   = "{{proxy+}}"
}}

resource "aws_api_gateway_method" "proxy" {{
  rest_api_id   = aws_api_gateway_rest_api.app.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}}

resource "aws_api_gateway_integration" "lambda" {{
  rest_api_id = aws_api_gateway_rest_api.app.id
  resource_id = aws_api_gateway_method.proxy.resource_id
  http_method = aws_api_gateway_method.proxy.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.app.invoke_arn
}}

resource "aws_api_gateway_deployment" "app" {{
  depends_on = [
    aws_api_gateway_integration.lambda,
  ]
  
  rest_api_id = aws_api_gateway_rest_api.app.id
  stage_name  = "prod"
}}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gw" {{
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${{aws_api_gateway_rest_api.app.execution_arn}}/*/*"
}}
"""
        
        # Generate variables.tf
        variables_tf = """
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "function_name" {
  description = "Lambda function name"
  type        = string
  default     = "llm-deploy-app"
}
"""
        
        # Generate outputs.tf
        outputs_tf = """
output "api_gateway_url" {
  description = "API Gateway URL"
  value       = aws_api_gateway_deployment.app.invoke_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.app.function_name
}

output "application_url" {
  description = "Application URL"
  value       = "${aws_api_gateway_deployment.app.invoke_url}/"
}
"""
        
        return {
            "main.tf": main_tf,
            "variables.tf": variables_tf,
            "outputs.tf": outputs_tf
        }


class KubernetesTerraformGenerator(LLMTerraformGenerator):
    """Generate Terraform for Kubernetes infrastructure (EKS)."""
    
    def generate_terraform_config(self, requirements: Dict[str, Any], analysis: Dict[str, Any], region: str, repo_url: str) -> Dict[str, str]:
        """Generate Kubernetes Terraform configuration."""
        
        infra_req = requirements.get("infrastructure_requirements", {})
        app_req = requirements.get("application_requirements", {})
        
        instance_type = infra_req.get("instance_type", "t3.medium")
        port = app_req.get("port", 5000)
        
        # Generate main.tf for EKS
        main_tf = f"""
terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
    kubernetes = {{
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }}
  }}
}}

provider "aws" {{
  region = "{region}"
}}

# EKS Cluster
resource "aws_eks_cluster" "main" {{
  name     = "llm-deploy-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  
  vpc_config {{
    subnet_ids = aws_subnet.private[*].id
  }}
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
}}

# EKS Node Group
resource "aws_eks_node_group" "main" {{
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "llm-deploy-nodes"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id
  
  scaling_config {{
    desired_size = 2
    max_size     = 4
    min_size     = 1
  }}
  
  instance_types = ["{instance_type}"]
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_read_only,
  ]
}}

# VPC
resource "aws_vpc" "main" {{
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {{
    Name = "llm-deploy-vpc"
  }}
}}

# Private Subnets
resource "aws_subnet" "private" {{
  count = 2
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${{count.index + 1}}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  tags = {{
    Name = "llm-deploy-private-subnet-${{count.index + 1}}"
    "kubernetes.io/role/internal-elb" = "1"
  }}
}}

# Internet Gateway
resource "aws_internet_gateway" "main" {{
  vpc_id = aws_vpc.main.id
  
  tags = {{
    Name = "llm-deploy-igw"
  }}
}}

# NAT Gateway
resource "aws_eip" "nat" {{
  count = 2
  
  domain = "vpc"
  
  tags = {{
    Name = "llm-deploy-nat-eip-${{count.index + 1}}"
  }}
}}

resource "aws_nat_gateway" "main" {{
  count = 2
  
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  
  tags = {{
    Name = "llm-deploy-nat-gateway-${{count.index + 1}}"
  }}
  
  depends_on = [aws_internet_gateway.main]
}}

# Public Subnets
resource "aws_subnet" "public" {{
  count = 2
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${{count.index + 10}}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {{
    Name = "llm-deploy-public-subnet-${{count.index + 1}}"
    "kubernetes.io/role/elb" = "1"
  }}
}}

# Route Tables
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

resource "aws_route_table" "private" {{
  count = 2
  
  vpc_id = aws_vpc.main.id
  
  route {{
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }}
  
  tags = {{
    Name = "llm-deploy-private-rt-${{count.index + 1}}"
  }}
}}

resource "aws_route_table_association" "public" {{
  count = 2
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}}

resource "aws_route_table_association" "private" {{
  count = 2
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}}

# IAM Roles
resource "aws_iam_role" "eks_cluster" {{
  name = "llm-deploy-eks-cluster-role"
  
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {{
          Service = "eks.amazonaws.com"
        }}
      }}
    ]
  }})
}}

resource "aws_iam_role" "eks_node_group" {{
  name = "llm-deploy-eks-node-group-role"
  
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {{
          Service = "ec2.amazonaws.com"
        }}
      }}
    ]
  }})
}}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {{
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {{
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_group.name
}}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {{
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_group.name
}}

resource "aws_iam_role_policy_attachment" "eks_container_registry_read_only" {{
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_group.name
}}

# Data sources
data "aws_availability_zones" "available" {{
  state = "available"
}}

# Kubernetes provider
provider "kubernetes" {{
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  
  exec {{
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.main.name]
  }}
}}

# Kubernetes Deployment
resource "kubernetes_deployment" "app" {{
  metadata {{
    name = "llm-deploy-app"
    labels = {{
      app = "llm-deploy-app"
    }}
  }}
  
  spec {{
    replicas = 2
    
    selector {{
      match_labels = {{
        app = "llm-deploy-app"
      }}
    }}
    
    template {{
      metadata {{
        labels = {{
          app = "llm-deploy-app"
        }}
      }}
      
      spec {{
        container {{
          image = "nginx:latest"  # Placeholder - would be built from repo
          name  = "app"
          
          port {{
            container_port = {port}
          }}
          
          env {{
            name  = "REPO_URL"
            value = "{repo_url}"
          }}
        }}
      }}
    }}
  }}
}}

# Kubernetes Service
resource "kubernetes_service" "app" {{
  metadata {{
    name = "llm-deploy-service"
  }}
  
  spec {{
    selector = {{
      app = "llm-deploy-app"
    }}
    
    port {{
      port        = 80
      target_port = {port}
    }}
    
    type = "LoadBalancer"
  }}
}}
"""
        
        # Generate variables.tf
        variables_tf = """
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "llm-deploy-cluster"
}
"""
        
        # Generate outputs.tf
        outputs_tf = """
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "load_balancer_hostname" {
  description = "Load balancer hostname"
  value       = kubernetes_service.app.status.0.load_balancer.0.ingress.0.hostname
}

output "application_url" {
  description = "Application URL"
  value       = "http://${kubernetes_service.app.status.0.load_balancer.0.ingress.0.hostname}"
}
"""
        
        return {
            "main.tf": main_tf,
            "variables.tf": variables_tf,
            "outputs.tf": outputs_tf
        }


def get_terraform_generator(infrastructure_type: str) -> LLMTerraformGenerator:
    """Get appropriate Terraform generator based on infrastructure type."""
    
    if infrastructure_type == "serverless":
        return ServerlessTerraformGenerator()
    elif infrastructure_type == "kubernetes":
        return KubernetesTerraformGenerator()
    else:
        return LLMTerraformGenerator()  # Default to VM
