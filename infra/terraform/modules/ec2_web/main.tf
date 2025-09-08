terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "random_id" "suffix" { byte_length = 2 }

locals {
  name = "${var.app_name}-${random_id.suffix.hex}"
  tags = merge({
    "Name"      = local.name,
    "ManagedBy" = "arvo"
  }, var.tags)
}

resource "aws_security_group" "web" {
  name        = "${local.name}-sg"
  description = "Web SG"
  vpc_id      = data.aws_vpc.default.id

  dynamic "ingress" {
    for_each = var.ingress_cidr
    content {
      from_port   = var.port
      to_port     = var.port
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_instance" "this" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.public.ids[0]
  vpc_security_group_ids = [aws_security_group.web.id]
  associate_public_ip_address = true
  user_data              = var.user_data
  key_name               = length(var.key_name) > 0 ? var.key_name : null

  tags = local.tags
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_eip" "this" {
  count    = var.associate_eip ? 1 : 0
  instance = aws_instance.this.id
  tags     = local.tags
}

locals {
  public_ip = var.associate_eip ? aws_eip.this[0].public_ip : aws_instance.this.public_ip
}

output "public_ip" { value = local.public_ip }
output "public_url" { value = "http://${local.public_ip}:${var.port}" }
output "instance_id" { value = aws_instance.this.id }
output "log_links" {
  value = {
    ec2_console = "https://console.aws.amazon.com/ec2/home?region=${var.region}#InstanceDetails:instanceId=${aws_instance.this.id}"
  }
}
output "destroy_hint" { value = "terraform destroy -auto-approve" }
