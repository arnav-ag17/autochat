variable "app_name" {
  type = string
}

variable "region" {
  type = string
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "port" {
  type    = number
  default = 8080
}

variable "health_path" {
  type    = string
  default = "/"
}

variable "user_data" {
  type    = string
  default = ""
}

variable "associate_eip" {
  type    = bool
  default = true
}

variable "key_name" {
  type    = string
  default = ""
}

variable "ingress_cidr" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "tags" {
  type    = map(string)
  default = {}
}

module "ec2_web" {
  source         = "../../modules/ec2_web"
  app_name       = var.app_name
  region         = var.region
  instance_type  = var.instance_type
  port           = var.port
  health_path    = var.health_path
  user_data      = var.user_data
  associate_eip  = var.associate_eip
  key_name       = var.key_name
  ingress_cidr   = var.ingress_cidr
  tags           = var.tags
}

output "public_url" {
  value = module.ec2_web.public_url
}

output "log_links" {
  value = module.ec2_web.log_links
}

output "destroy_hint" {
  value = module.ec2_web.destroy_hint
}

output "instance_id"  {
  value = module.ec2_web.instance_id
}
