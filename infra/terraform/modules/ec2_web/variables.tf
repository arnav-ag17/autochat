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
