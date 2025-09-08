"""
Resource sweep utilities for finding and cleaning up tagged resources.
"""

import boto3
from typing import List, Tuple, Dict, Any
from botocore.exceptions import ClientError
import logging

from .models import FoundResource

logger = logging.getLogger(__name__)


def list_tagged_resources(region: str, deployment_id: str) -> List[FoundResource]:
    """
    List all AWS resources tagged with project=arvo and deployment_id=<id>.
    
    Args:
        region: AWS region
        deployment_id: Deployment ID to search for
        
    Returns:
        List of found resources
    """
    found_resources = []
    
    try:
        # Use Resource Groups Tagging API (preferred method)
        resource_groups = boto3.client('resourcegroupstaggingapi', region_name=region)
        
        # Search for resources with our tags
        paginator = resource_groups.get_paginator('get_resources')
        
        for page in paginator.paginate(
            TagFilters=[
                {
                    'Key': 'project',
                    'Values': ['arvo']
                },
                {
                    'Key': 'deployment_id', 
                    'Values': [deployment_id]
                }
            ]
        ):
            for resource in page.get('ResourceTagMappingList', []):
                arn = resource['ResourceARN']
                tags = {tag['Key']: tag['Value'] for tag in resource.get('Tags', [])}
                
                # Determine service from ARN
                service = _extract_service_from_arn(arn)
                
                found_resources.append(FoundResource(
                    service=service,
                    arn_or_id=arn,
                    tags=tags,
                    reason=f"Tagged with project=arvo and deployment_id={deployment_id}"
                ))
    
    except ClientError as e:
        logger.warning(f"Resource Groups Tagging API failed: {e}")
        # Fallback to targeted service calls
        found_resources = _fallback_resource_search(region, deployment_id)
    
    return found_resources


def _extract_service_from_arn(arn: str) -> str:
    """Extract service name from AWS ARN."""
    try:
        # ARN format: arn:partition:service:region:account-id:resource-type/resource
        parts = arn.split(':')
        if len(parts) >= 3:
            service = parts[2]
            # Map some services to more specific types
            if service == 'ec2':
                if 'instance' in arn:
                    return 'ec2'
                elif 'security-group' in arn:
                    return 'sg'
                elif 'elastic-ip' in arn:
                    return 'eip'
            elif service == 'elasticloadbalancing':
                if 'loadbalancer' in arn:
                    return 'alb'
                elif 'targetgroup' in arn:
                    return 'tg'
                elif 'listener' in arn:
                    return 'listener'
            elif service == 'ecs':
                if 'service' in arn:
                    return 'ecs'
                elif 'task-definition' in arn:
                    return 'task-def'
            elif service == 'ecr':
                return 'ecr'
            elif service == 'logs':
                return 'logs'
            elif service == 's3':
                return 's3'
            elif service == 'cloudfront':
                return 'cloudfront'
            elif service == 'iam':
                return 'iam'
            return service
    except Exception:
        pass
    
    return 'unknown'


def _fallback_resource_search(region: str, deployment_id: str) -> List[FoundResource]:
    """
    Fallback method using targeted service calls when Resource Groups API fails.
    
    Args:
        region: AWS region
        deployment_id: Deployment ID to search for
        
    Returns:
        List of found resources
    """
    found_resources = []
    
    # Search EC2 resources
    try:
        ec2 = boto3.client('ec2', region_name=region)
        
        # Search instances
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:project', 'Values': ['arvo']},
                {'Name': 'tag:deployment_id', 'Values': [deployment_id]}
            ]
        )
        
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                found_resources.append(FoundResource(
                    service='ec2',
                    arn_or_id=instance['InstanceId'],
                    tags=tags,
                    reason=f"EC2 instance tagged with deployment_id={deployment_id}"
                ))
        
        # Search security groups
        response = ec2.describe_security_groups(
            Filters=[
                {'Name': 'tag:project', 'Values': ['arvo']},
                {'Name': 'tag:deployment_id', 'Values': [deployment_id]}
            ]
        )
        
        for sg in response.get('SecurityGroups', []):
            tags = {tag['Key']: tag['Value'] for tag in sg.get('Tags', [])}
            found_resources.append(FoundResource(
                service='sg',
                arn_or_id=sg['GroupId'],
                tags=tags,
                reason=f"Security group tagged with deployment_id={deployment_id}"
            ))
    
    except ClientError as e:
        logger.warning(f"EC2 search failed: {e}")
    
    # Search CloudWatch Logs
    try:
        logs = boto3.client('logs', region_name=region)
        
        response = logs.describe_log_groups(
            logGroupNamePrefix=f'/arvo/{deployment_id}'
        )
        
        for log_group in response.get('logGroups', []):
            tags = {}
            try:
                tag_response = logs.list_tags_log_group(logGroupName=log_group['logGroupName'])
                tags = tag_response.get('tags', {})
            except ClientError:
                pass
            
            found_resources.append(FoundResource(
                service='logs',
                arn_or_id=log_group['logGroupName'],
                tags=tags,
                reason=f"CloudWatch log group for deployment_id={deployment_id}"
            ))
    
    except ClientError as e:
        logger.warning(f"CloudWatch Logs search failed: {e}")
    
    # Search S3 buckets
    try:
        s3 = boto3.client('s3', region_name=region)
        
        response = s3.list_buckets()
        for bucket in response.get('Buckets', []):
            try:
                tag_response = s3.get_bucket_tagging(Bucket=bucket['Name'])
                tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}
                
                if (tags.get('project') == 'arvo' and 
                    tags.get('deployment_id') == deployment_id):
                    found_resources.append(FoundResource(
                        service='s3',
                        arn_or_id=bucket['Name'],
                        tags=tags,
                        reason=f"S3 bucket tagged with deployment_id={deployment_id}"
                    ))
            except ClientError:
                # Bucket might not have tags or we might not have permission
                continue
    
    except ClientError as e:
        logger.warning(f"S3 search failed: {e}")
    
    return found_resources


def nuke_if_leftovers(found: List[FoundResource]) -> Tuple[int, int]:
    """
    Attempt to delete leftover resources.
    
    Args:
        found: List of found resources to delete
        
    Returns:
        Tuple of (removed_count, failed_count)
    """
    removed = 0
    failed = 0
    
    for resource in found:
        try:
            if _delete_resource(resource):
                removed += 1
                logger.info(f"Deleted {resource.service} resource: {resource.arn_or_id}")
            else:
                failed += 1
                logger.warning(f"Failed to delete {resource.service} resource: {resource.arn_or_id}")
        except Exception as e:
            failed += 1
            logger.error(f"Error deleting {resource.service} resource {resource.arn_or_id}: {e}")
    
    return removed, failed


def _delete_resource(resource: FoundResource) -> bool:
    """
    Delete a specific resource based on its type.
    
    Args:
        resource: Resource to delete
        
    Returns:
        True if deletion was successful or not needed, False otherwise
    """
    try:
        # Extract region from ARN if possible
        region = _extract_region_from_arn(resource.arn_or_id) or 'us-west-2'
        
        if resource.service == 'ec2':
            return _delete_ec2_instance(resource.arn_or_id, region)
        elif resource.service == 'sg':
            return _delete_security_group(resource.arn_or_id, region)
        elif resource.service == 'logs':
            return _delete_log_group(resource.arn_or_id, region)
        elif resource.service == 's3':
            return _delete_s3_bucket(resource.arn_or_id, region)
        elif resource.service == 'ecr':
            return _delete_ecr_repository(resource.arn_or_id, region)
        else:
            logger.warning(f"Don't know how to delete {resource.service} resource: {resource.arn_or_id}")
            return False
    
    except Exception as e:
        logger.error(f"Error in _delete_resource for {resource.service} {resource.arn_or_id}: {e}")
        return False


def _extract_region_from_arn(arn: str) -> str:
    """Extract region from AWS ARN."""
    try:
        parts = arn.split(':')
        if len(parts) >= 4:
            return parts[3]
    except Exception:
        pass
    return None


def _delete_ec2_instance(instance_id: str, region: str) -> bool:
    """Delete EC2 instance."""
    try:
        ec2 = boto3.client('ec2', region_name=region)
        ec2.terminate_instances(InstanceIds=[instance_id])
        return True
    except ClientError as e:
        logger.error(f"Failed to delete EC2 instance {instance_id}: {e}")
        return False


def _delete_security_group(group_id: str, region: str) -> bool:
    """Delete security group."""
    try:
        ec2 = boto3.client('ec2', region_name=region)
        ec2.delete_security_group(GroupId=group_id)
        return True
    except ClientError as e:
        logger.error(f"Failed to delete security group {group_id}: {e}")
        return False


def _delete_log_group(log_group_name: str, region: str) -> bool:
    """Delete CloudWatch log group."""
    try:
        logs = boto3.client('logs', region_name=region)
        logs.delete_log_group(logGroupName=log_group_name)
        return True
    except ClientError as e:
        logger.error(f"Failed to delete log group {log_group_name}: {e}")
        return False


def _delete_s3_bucket(bucket_name: str, region: str) -> bool:
    """Delete S3 bucket (empty it first)."""
    try:
        s3 = boto3.client('s3', region_name=region)
        
        # List and delete all objects
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
        
        # Delete the bucket
        s3.delete_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        logger.error(f"Failed to delete S3 bucket {bucket_name}: {e}")
        return False


def _delete_ecr_repository(repo_name: str, region: str) -> bool:
    """Delete ECR repository."""
    try:
        ecr = boto3.client('ecr', region_name=region)
        ecr.delete_repository(repositoryName=repo_name, force=True)
        return True
    except ClientError as e:
        logger.error(f"Failed to delete ECR repository {repo_name}: {e}")
        return False
