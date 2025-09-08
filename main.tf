terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = "us-west-2" }

# Use the ec2_web module
module "ec2_web" {
  source = "./infra/terraform/modules/ec2_web"
  
  app_name = "arvo-demo"
  region   = "us-west-2"
  
  # Use tags from terraform.tfvars.json if provided
  tags = var.tags
}

# Variables
variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to all resources"
}

# Outputs are defined in outputs.tf
