# ec2_web module

Inputs:
- app_name (string)
- region (string)
- instance_type (string, default t3.micro)
- port (number, default 8080)
- health_path (string, default /)
- user_data (string)
- associate_eip (bool, default true)
- key_name (string, optional)
- ingress_cidr (list(string), default ["0.0.0.0/0"]) 
- tags (map(string))

Outputs:
- public_url
- instance_id
- log_links (ec2_console)
- destroy_hint
