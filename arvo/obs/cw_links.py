"""
CloudWatch and AWS console link builders.
"""

import urllib.parse
from typing import Dict, Optional


class CloudWatchLinkBuilder:
    """Builds AWS console URLs for logs and resources."""
    
    def __init__(self, region: str):
        self.region = region
    
    def build_log_group_url(self, log_group: str) -> str:
        """Build CloudWatch log group console URL."""
        encoded_group = urllib.parse.quote(log_group, safe='')
        return f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#logsV2:log-groups/log-group/{encoded_group}"
    
    def build_log_stream_url(self, log_group: str, log_stream: str) -> str:
        """Build CloudWatch log stream console URL."""
        encoded_group = urllib.parse.quote(log_group, safe='')
        encoded_stream = urllib.parse.quote(log_stream, safe='')
        return f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#logsV2:log-groups/log-group/{encoded_group}/log-events/{encoded_stream}"
    
    def build_ec2_console_url(self, instance_id: str) -> str:
        """Build EC2 instance console URL."""
        return f"https://console.aws.amazon.com/ec2/home?region={self.region}#InstanceDetails:instanceId={instance_id}"
    
    def build_ecs_service_url(self, cluster_name: str, service_name: str) -> str:
        """Build ECS service console URL."""
        return f"https://console.aws.amazon.com/ecs/home?region={self.region}#/clusters/{cluster_name}/services/{service_name}/details"
    
    def build_alb_console_url(self, alb_arn: str) -> str:
        """Build ALB console URL."""
        # Extract ALB name from ARN
        alb_name = alb_arn.split('/')[-1] if '/' in alb_arn else alb_arn
        return f"https://console.aws.amazon.com/ec2/home?region={self.region}#LoadBalancers:search={alb_name}"
    
    def build_cloudfront_console_url(self, distribution_id: str) -> str:
        """Build CloudFront distribution console URL."""
        return f"https://console.aws.amazon.com/cloudfront/home?region={self.region}#/distributions/{distribution_id}"
    
    def build_s3_console_url(self, bucket_name: str) -> str:
        """Build S3 bucket console URL."""
        return f"https://console.aws.amazon.com/s3/buckets/{bucket_name}?region={self.region}"
    
    def build_log_links(self, deployment_id: str, outputs: Dict[str, str]) -> Dict[str, str]:
        """Build comprehensive log links based on deployment outputs."""
        links = {}
        
        # CloudWatch log group (always present)
        log_group = f"/arvo/{deployment_id}"
        links["cloudwatch_group"] = self.build_log_group_url(log_group)
        
        # EC2 specific links
        if "instance_id" in outputs:
            links["ec2_console"] = self.build_ec2_console_url(outputs["instance_id"])
            links["ec2_cloud_init"] = self.build_log_stream_url(log_group, "ec2/cloud-init")
            links["ec2_systemd"] = self.build_log_stream_url(log_group, "ec2/service")
        
        # ECS specific links
        if "service_arn" in outputs:
            # Extract cluster and service from ARN
            arn_parts = outputs["service_arn"].split('/')
            if len(arn_parts) >= 3:
                cluster_name = arn_parts[1]
                service_name = arn_parts[2]
                links["ecs_service_console"] = self.build_ecs_service_url(cluster_name, service_name)
                links["ecs_task_logs"] = self.build_log_stream_url(log_group, f"ecs/{service_name}")
        
        # ALB specific links
        if "alb_arn" in outputs:
            links["alb_console"] = self.build_alb_console_url(outputs["alb_arn"])
        
        # CloudFront specific links
        if "distribution_id" in outputs:
            links["cloudfront_console"] = self.build_cloudfront_console_url(outputs["distribution_id"])
        
        # S3 specific links
        if "bucket_name" in outputs:
            links["s3_console"] = self.build_s3_console_url(outputs["bucket_name"])
        
        return links
    
    def build_tail_command(self, log_group: str, log_stream: Optional[str] = None) -> str:
        """Build AWS CLI command to tail logs."""
        cmd = f"aws logs tail {log_group} --region {self.region}"
        if log_stream:
            cmd += f" --log-stream-names {log_stream}"
        cmd += " --follow"
        return cmd
