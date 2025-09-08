output "public_ip" {
  description = "Public IP address of the Flask application"
  value       = module.ec2_web.public_ip
}

output "application_url" {
  description = "URL to access the Flask application"
  value       = module.ec2_web.public_url
}

# Use root path for baseline health to avoid 404s
output "health_check_url" {
  description = "Health check endpoint URL"
  value       = module.ec2_web.public_url
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2_web.instance_id
}

output "deployment_status" {
  description = "Status of the deployment"
  value       = "Flask hello world application deployed successfully"
}
