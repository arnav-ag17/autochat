"""
Main orchestrator for deployment lifecycle management.
"""

import time
import requests
from typing import Dict, Any, Optional

from .ids import new_deployment_id
from .state import (
    create_deployment_dir, write_env_json, write_outputs_json,
    read_env_json, read_outputs_json, deployment_exists
)
from .events import emit_event, EventTypes, get_status_from_events, read_events
from .terraform import tf_init, tf_plan, tf_apply, tf_destroy, get_terraform_outputs, get_terraform_output
from arvo.selector import select_infra
from arvo.analyzer.spec import DeploymentSpec
from .obs import StreamManager, LogSource, FailureClassifier, StatusDeriver, CloudWatchLinkBuilder
from .tags import base_tags, add_ttl_tags
from .cost import estimate_cost, format_cost_hint
from .ttl import schedule_ttl_deployment
from .cleanup import list_tagged_resources, nuke_if_leftovers
from .envman import delete_parameters
from .analyzer import analyze_repo
from .recipes import select_recipe, run_smoke_test
from .nlp import extract_overrides


def deploy(instructions: str, repo: str, region: str = "us-west-2", deployment_id: Optional[str] = None, 
          user_tags: Optional[Dict[str, str]] = None, ttl_hours: Optional[int] = None) -> Dict[str, Any]:
    """
    Deploy an application using Terraform.
    
    Args:
        instructions: Deployment instructions
        repo: Repository URL
        region: AWS region
        deployment_id: Optional deployment ID (generated if not provided)
        user_tags: Optional user-provided tags
        ttl_hours: Optional TTL in hours for auto-destroy
        
    Returns:
        Deployment result dictionary
    """
    if deployment_id is None:
        deployment_id = new_deployment_id()
    
    # Initialize deployment
    create_deployment_dir(deployment_id)
    write_env_json(deployment_id, instructions, repo, region)
    
    # Generate tags
    tags = base_tags(deployment_id, user_tags)
    if ttl_hours:
        tags = add_ttl_tags(tags, ttl_hours)
    
    emit_event(deployment_id, EventTypes.INIT, {
        "deployment_id": deployment_id,
        "region": region,
        "repo": repo,
        "instructions": instructions,
        "ttl_hours": ttl_hours
    })
    
    emit_event(deployment_id, EventTypes.TAGS_APPLIED, {
        "count": len(tags),
        "sample": dict(list(tags.items())[:3])  # Show first 3 tags
    })

    # Stage 1: NLP extraction
    try:
        nlp_overrides, nlp_report = extract_overrides(
            instructions,
            default_cloud="aws",
            default_region=region,
            timeout_s=15.0
        )
        
        emit_event(deployment_id, EventTypes.NLP_PASS_A, {
            "hits": nlp_report.passA_hits
        })
        
        emit_event(deployment_id, EventTypes.NLP_PASS_B, {
            "provider": nlp_report.raw_provider,
            "model": nlp_report.raw_provider.split(":")[1] if ":" in nlp_report.raw_provider else "default",
            "used_examples": 3,  # We use 3 examples
            "took_ms": nlp_report.duration_ms
        })
        
        emit_event(deployment_id, EventTypes.NLP_OVERRIDES, {
            "cloud": nlp_overrides.cloud,
            "infra": nlp_overrides.infra,
            "region": nlp_overrides.region,
            "size": nlp_overrides.instance_size,
            "domain": nlp_overrides.domain,
            "ssl": nlp_overrides.ssl,
            "autoscale": nlp_overrides.autoscale,
            "confidence": nlp_overrides.confidence,
            "assumptions": nlp_report.assumptions,
            "conflicts": nlp_report.conflicts
        })
        
        # Merge NLP overrides with user-provided overrides
        if nlp_overrides.ttl_hours and not ttl_hours:
            ttl_hours = nlp_overrides.ttl_hours
        
        if nlp_overrides.env_overrides and not user_tags:
            user_tags = nlp_overrides.env_overrides
        elif nlp_overrides.env_overrides and user_tags:
            user_tags.update(nlp_overrides.env_overrides)
        
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"NLP extraction failed: {e}",
            "hint": "Proceeding with default configuration"
        })
        nlp_overrides = None

    # Stage 2: Analyze repository
    try:
        from .state import get_deployment_dir
        deployment_dir = get_deployment_dir(deployment_id)
        workspace_path = str(deployment_dir / "workspace")
        
        # Fetch and analyze the repository
        checkout_path, commit_hint = analyze_repo.fetch_into_workspace(repo, workspace_path)
        spec = analyze_repo.analyze_repo(checkout_path, instructions)
        
        emit_event(deployment_id, EventTypes.ANALYZE_DONE, {
            "runtime": spec.runtime,
            "framework": spec.framework,
            "containerized": spec.containerized,
            "port": spec.port,
            "health_path": spec.health_path,
            "warnings": spec.warnings,
            "rationale": spec.rationale
        })
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Repository analysis failed: {e}",
            "hint": "Using fallback configuration"
        })
        # Fallback to basic spec
        spec = DeploymentSpec(
            app_path=".", runtime="python", framework="flask",
            containerized=False, multi_service=False,
            start_command=None, port=8080,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={}, extra={}
        )

    # Stage 3: Infra selection
    try:
        infra_plan = select_infra(spec, overrides=None)
        emit_event(deployment_id, EventTypes.INFRA_DECISION, {
            "target": infra_plan.target,
            "module_hint": infra_plan.module_hint,
            "parameters": infra_plan.parameters,
            "rationale": infra_plan.rationale,
            "warnings": infra_plan.warnings,
            "confidence": infra_plan.confidence,
            "fallback_used": infra_plan.fallback_used,
        })
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Infrastructure selection failed: {e}",
            "hint": "Using default EC2 configuration"
        })
        # Fallback to basic infra plan
        from .selector import InfraPlan
        infra_plan = InfraPlan(
            target="ec2", module_hint="ec2_web", parameters={},
            rationale=["Fallback to EC2"], warnings=[], confidence=0.5, fallback_used=True
        )

    # Stage 9: Recipe selection
    try:
        recipe = select_recipe(spec, infra_plan)
        if recipe:
            # Stage 5: Patcher (placeholder - would integrate with existing patcher)
            patch_result = {"patched": True, "notes": ["Recipe-based patching"]}
            
            # Stage 6: Environment injection (placeholder - would integrate with existing envman)
            env_inject = {"injected": True, "env_count": len(spec.env_required)}
            
            # Generate recipe plan
            recipe_plan = recipe.plan(spec, infra_plan, patch_result, env_inject, repo)
            
            emit_event(deployment_id, EventTypes.RECIPE_SELECTED, {
                "name": recipe_plan.name,
                "target": recipe_plan.target,
                "rationale": recipe_plan.rationale,
                "preflight_notes": recipe_plan.preflight_notes
            })
        else:
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": "No suitable recipe found",
                "hint": "Using default deployment configuration"
            })
            recipe_plan = None
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Recipe selection failed: {e}",
            "hint": "Using default deployment configuration"
        })
        recipe_plan = None

    try:
        # Terraform workflow
        if not tf_init(deployment_id):
            return _create_error_result(deployment_id, "Terraform init failed")
        
        if not tf_plan(deployment_id):
            return _create_error_result(deployment_id, "Terraform plan failed")
        
        # Cost estimation before apply
        try:
            from .state import get_deployment_dir
            deployment_dir = get_deployment_dir(deployment_id)
            stack_path = str(deployment_dir / "terraform")
            
            cost_data = estimate_cost(stack_path, region)
            emit_event(deployment_id, EventTypes.COST_HINT, cost_data)
        except Exception as e:
            # Don't fail deployment if cost estimation fails
            emit_event(deployment_id, EventTypes.COST_HINT, {
                "method": "error",
                "monthly_usd": None,
                "error": str(e)
            })
        
        # Use recipe plan variables if available
        tf_vars = {"tags": tags}
        if recipe_plan:
            tf_vars.update(recipe_plan.vars)
            # Add user_data if available (separate from tags)
            if recipe_plan.user_data:
                tf_vars["user_data"] = recipe_plan.user_data
        
        if not tf_apply(deployment_id, tf_vars):
            return _create_error_result(deployment_id, "Terraform apply failed")
        
        # Wait for bootstrap
        emit_event(deployment_id, EventTypes.BOOTSTRAP_WAIT, {
            "message": "Waiting for application to bootstrap..."
        })
        
        # Get outputs
        outputs = get_terraform_outputs(deployment_id)
        write_outputs_json(deployment_id, outputs)
        
        public_url = get_terraform_output(deployment_id, "application_url")
        if not public_url:
            return _create_error_result(deployment_id, "Failed to get application URL")
        
        # Start observability streaming
        _start_observability_streaming(deployment_id, region, outputs)
        
        # Verify deployment with smoke tests
        if _verify_deployment(deployment_id, public_url, recipe_plan):
            result = _create_success_result(deployment_id, public_url, outputs, region)
            
            # Schedule TTL if specified
            if ttl_hours:
                try:
                    ttl_data = schedule_ttl_deployment(deployment_id, ttl_hours)
                    emit_event(deployment_id, EventTypes.TTL_SCHEDULED, ttl_data)
                except Exception as e:
                    # Don't fail deployment if TTL scheduling fails
                    emit_event(deployment_id, EventTypes.ERROR, {
                        "reason": f"TTL scheduling failed: {e}",
                        "hint": "Deployment succeeded but auto-destroy not scheduled"
                    })
            
            emit_event(deployment_id, EventTypes.DONE, result)
            return result
        else:
            return _create_error_result(deployment_id, "Application verification failed")
            
    except Exception as e:
        return _create_error_result(deployment_id, f"Deployment failed: {str(e)}")


def _verify_deployment(deployment_id: str, public_url: str, recipe_plan=None, max_wait: int = 120) -> bool:
    """
    Verify that the deployed application is responding using smoke tests.
    
    Args:
        deployment_id: Deployment ID
        public_url: Public URL to test
        recipe_plan: Recipe plan with smoke checks (optional)
        max_wait: Maximum wait time in seconds
        
    Returns:
        True if verification successful
    """
    # If we have a recipe plan with smoke checks, use them
    if recipe_plan and recipe_plan.smoke_checks:
        emit_event(deployment_id, EventTypes.SMOKE_ATTEMPT, {
            "path": "all",
            "try": 1,
            "total": len(recipe_plan.smoke_checks)
        })
        
        try:
            smoke_result = run_smoke_test(public_url, recipe_plan.smoke_checks, max_retries=max_wait//5, retry_delay=5)
            
            if smoke_result.success:
                emit_event(deployment_id, EventTypes.SMOKE_OK, {
                    "path": "all",
                    "code": 200,
                    "details": smoke_result.details
                })
                return True
            else:
                # Emit failure for first failed check
                if smoke_result.details.get("failed_checks"):
                    first_failure = smoke_result.details["failed_checks"][0]
                    emit_event(deployment_id, EventTypes.SMOKE_FAIL, {
                        "path": first_failure["path"],
                        "code": first_failure.get("status", "unknown"),
                        "hint": first_failure["error"],
                        "body_snippet": "Check failed"
                    })
                return False
        except Exception as e:
            emit_event(deployment_id, EventTypes.SMOKE_FAIL, {
                "path": "all",
                "code": "error",
                "hint": f"Smoke test error: {e}",
                "body_snippet": "Test execution failed"
            })
            return False
    else:
        # Fallback to simple health check
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(public_url, timeout=10)
                if response.status_code == 200:
                    emit_event(deployment_id, EventTypes.VERIFY_OK, {
                        "url": public_url,
                        "code": response.status_code
                    })
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(3)
        
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": "Application verification timeout",
            "hint": "Service not up; check bootstrap or security group"
        })
        return False


def _create_success_result(deployment_id: str, public_url: str, outputs: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Create a success result dictionary.
    
    Args:
        deployment_id: Deployment ID
        public_url: Public URL
        outputs: Terraform outputs
        region: AWS region
        
    Returns:
        Success result dictionary
    """
    # Build log links
    link_builder = CloudWatchLinkBuilder(region)
    log_links = link_builder.build_log_links(deployment_id, outputs)
    
    result = {
        "deployment_id": deployment_id,
        "status": "healthy",
        "public_url": public_url,
        "logs_location": f".arvo/{deployment_id}/logs.ndjson",
        "destroy_cmd": f"arvo destroy {deployment_id}",
        "log_links": log_links
    }
    
    # Emit DONE_WITH_LOGS event
    emit_event(deployment_id, EventTypes.DONE_WITH_LOGS, {
        "public_url": public_url,
        "log_links": log_links
    })
    
    return result


def _create_error_result(deployment_id: str, reason: str) -> Dict[str, Any]:
    """
    Create an error result dictionary.
    
    Args:
        deployment_id: Deployment ID
        reason: Error reason
        
    Returns:
        Error result dictionary
    """
    emit_event(deployment_id, EventTypes.ERROR, {
        "reason": reason,
        "hint": "Check logs for details"
    })
    
    return {
        "deployment_id": deployment_id,
        "status": "failed",
        "public_url": None,
        "logs_location": f".arvo/{deployment_id}/logs.ndjson",
        "destroy_cmd": f"arvo destroy {deployment_id}",
        "error": reason
    }


def status(deployment_id: str) -> Dict[str, Any]:
    """
    Get deployment status with comprehensive information.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Status dictionary
    """
    if not deployment_exists(deployment_id):
        return {
            "deployment_id": deployment_id,
            "status": "not_found"
        }
    
    # Use StatusDeriver for comprehensive status
    events = read_events(deployment_id)
    outputs = read_outputs_json(deployment_id)
    
    status_deriver = StatusDeriver()
    status_info = status_deriver.derive_status(events, outputs)
    
    result = {
        "deployment_id": deployment_id,
        "status": status_info.status.value,
        "message": status_info.message,
        "timestamp": status_info.timestamp
    }
    
    # Add public URL if available
    if status_info.public_url:
        result["public_url"] = status_info.public_url
    
    # Add log links if available
    if status_info.log_links:
        result["log_links"] = status_info.log_links
    
    # Add failure information if failed
    if status_info.failure_reason:
        result["failure_reason"] = status_info.failure_reason
        result["failure_hint"] = status_info.failure_hint
    
    return result


def outputs(deployment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get deployment outputs.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Outputs dictionary or None if not found
    """
    if not deployment_exists(deployment_id):
        return None
    
    return read_outputs_json(deployment_id)


def logs(deployment_id: str) -> list[Dict[str, Any]]:
    """
    Get deployment logs.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        List of log events
    """
    if not deployment_exists(deployment_id):
        return []
    
    from .events import read_events
    return read_events(deployment_id)


def destroy(deployment_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Destroy a deployment with comprehensive cleanup.
    
    Args:
        deployment_id: Deployment ID
        force: Force destroy without confirmation
        
    Returns:
        Destroy result dictionary
    """
    if not deployment_exists(deployment_id):
        return {
            "deployment_id": deployment_id,
            "status": "not_found"
        }
    
    emit_event(deployment_id, EventTypes.DESTROY_START, {
        "deployment_id": deployment_id,
        "force": force
    })
    
    try:
        # Get deployment region
        env_data = read_env_json(deployment_id)
        region = env_data.get("region", "us-west-2")
        
        # Run Terraform destroy
        success = tf_destroy(deployment_id)
        
        # Post-destroy cleanup sweep
        cleanup_results = _post_destroy_cleanup(deployment_id, region)
        
        if success:
            result = {
                "deployment_id": deployment_id,
                "status": "destroyed",
                "cleanup": cleanup_results
            }
            emit_event(deployment_id, EventTypes.DESTROY_DONE, result)
            return result
        else:
            result = {
                "deployment_id": deployment_id,
                "status": "destroy_failed",
                "cleanup": cleanup_results
            }
            emit_event(deployment_id, EventTypes.DESTROY_DONE, result)
            return result
            
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Destroy failed: {str(e)}",
            "hint": "Check terraform state and AWS credentials"
        })
        return {
            "deployment_id": deployment_id,
            "status": "destroy_failed",
            "error": str(e)
        }


def _start_observability_streaming(deployment_id: str, region: str, outputs: Dict[str, Any]):
    """
    Start observability streaming for runtime logs.
    
    Args:
        deployment_id: Deployment ID
        region: AWS region
        outputs: Terraform outputs
    """
    def event_callback(event_type: str, data: Dict[str, Any]):
        """Callback for streaming events."""
        emit_event(deployment_id, event_type, data)
        
        # Check for failures in runtime logs
        if event_type == "OBS_LINE":
            message = data.get("message", "")
            source = data.get("source", "unknown")
            
            classifier = FailureClassifier()
            failure = classifier.detect_failure(message, source)
            if failure:
                emit_event(deployment_id, EventTypes.FAILURE_DETECTED, failure)
    
    # Create stream manager
    stream_manager = StreamManager(deployment_id, region, event_callback)
    
    # Add CloudWatch log streams based on infrastructure type
    log_group = f"/arvo/{deployment_id}"
    
    # Check if this is EC2 deployment
    if "instance_id" in outputs:
        stream_manager.add_stream("ec2_cloud_init", LogSource.EC2_CLOUD_INIT, log_group, "ec2/cloud-init")
        stream_manager.add_stream("ec2_systemd", LogSource.EC2_SYSTEMD, log_group, "ec2/service")
        
        # Start streaming after a short delay to allow logs to appear
        import threading
        def delayed_start():
            import time
            time.sleep(30)  # Wait 30 seconds for CloudWatch logs to appear
            stream_manager.start_streaming("ec2_cloud_init")
            stream_manager.start_streaming("ec2_systemd")
            stream_manager.emit_cloudwatch_ready("ec2_cloud_init")
            stream_manager.emit_cloudwatch_ready("ec2_systemd")
        
        thread = threading.Thread(target=delayed_start, daemon=True)
        thread.start()


def _post_destroy_cleanup(deployment_id: str, region: str) -> Dict[str, Any]:
    """
    Perform post-destroy cleanup sweep.
    
    Args:
        deployment_id: Deployment ID
        region: AWS region
        
    Returns:
        Cleanup results
    """
    cleanup_results = {
        "ssm_deleted": 0,
        "log_groups_deleted": 0,
        "tagged_resources_found": 0,
        "tagged_resources_removed": 0,
        "tagged_resources_failed": 0
    }
    
    try:
        # Delete SSM parameters
        try:
            delete_parameters(deployment_id, region)
            cleanup_results["ssm_deleted"] = 1
        except Exception as e:
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": f"SSM cleanup failed: {e}",
                "hint": "SSM parameters may need manual cleanup"
            })
        
        # Delete CloudWatch log groups
        try:
            import boto3
            logs = boto3.client('logs', region_name=region)
            log_group_name = f"/arvo/{deployment_id}"
            
            try:
                logs.delete_log_group(logGroupName=log_group_name)
                cleanup_results["log_groups_deleted"] = 1
            except logs.exceptions.ResourceNotFoundException:
                # Log group doesn't exist, that's fine
                pass
        except Exception as e:
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": f"CloudWatch logs cleanup failed: {e}",
                "hint": "Log groups may need manual cleanup"
            })
        
        # Scan for tagged resources
        try:
            found_resources = list_tagged_resources(region, deployment_id)
            cleanup_results["tagged_resources_found"] = len(found_resources)
            
            if found_resources:
                emit_event(deployment_id, EventTypes.GC_SCAN, {
                    "remaining": len(found_resources),
                    "resources": [{"service": r.service, "arn_or_id": r.arn_or_id} for r in found_resources]
                })
                
                # Attempt to clean up leftover resources
                removed, failed = nuke_if_leftovers(found_resources)
                cleanup_results["tagged_resources_removed"] = removed
                cleanup_results["tagged_resources_failed"] = failed
                
                emit_event(deployment_id, EventTypes.GC_CLEANED, {
                    "removed": removed,
                    "failed": failed
                })
        
        except Exception as e:
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": f"Resource sweep failed: {e}",
                "hint": "Some resources may need manual cleanup"
            })
    
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Cleanup sweep failed: {e}",
            "hint": "Manual cleanup may be required"
        })
    
    return cleanup_results


def _start_observability_streaming(deployment_id: str, region: str, outputs: Dict[str, Any]):
    """
    Start observability streaming for runtime logs.
    
    Args:
        deployment_id: Deployment ID
        region: AWS region
        outputs: Terraform outputs
    """
    def event_callback(event_type: str, data: Dict[str, Any]):
        """Callback for streaming events."""
        emit_event(deployment_id, event_type, data)
        
        # Check for failures in runtime logs
        if event_type == "OBS_LINE":
            message = data.get("message", "")
            source = data.get("source", "unknown")
            
            classifier = FailureClassifier()
            failure = classifier.detect_failure(message, source)
            if failure:
                emit_event(deployment_id, EventTypes.FAILURE_DETECTED, failure)
    
    # Create stream manager
    stream_manager = StreamManager(deployment_id, region, event_callback)
    
    # Add CloudWatch log streams based on infrastructure type
    log_group = f"/arvo/{deployment_id}"
    
    # Check if this is EC2 deployment
    if "instance_id" in outputs:
        stream_manager.add_stream("ec2_cloud_init", LogSource.EC2_CLOUD_INIT, log_group, "ec2/cloud-init")
        stream_manager.add_stream("ec2_systemd", LogSource.EC2_SYSTEMD, log_group, "ec2/service")
        
        # Start streaming after a short delay to allow logs to appear
        import threading
        def delayed_start():
            import time
            time.sleep(30)  # Wait 30 seconds for CloudWatch logs to appear
            stream_manager.start_streaming("ec2_cloud_init")
            stream_manager.start_streaming("ec2_systemd")
            stream_manager.emit_cloudwatch_ready("ec2_cloud_init")
            stream_manager.emit_cloudwatch_ready("ec2_systemd")
        
        thread = threading.Thread(target=delayed_start, daemon=True)
        thread.start()
    
    # Check if this is ECS deployment
    elif "service_arn" in outputs:
        # Extract service name from ARN
        service_name = outputs["service_arn"].split("/")[-1] if "/" in outputs["service_arn"] else "service"
        stream_manager.add_stream("ecs_task", LogSource.ECS_TASK, log_group, f"ecs/{service_name}")
        
        # Start streaming
        import threading
        def delayed_start():
            import time
            time.sleep(30)  # Wait 30 seconds for ECS logs to appear
            stream_manager.start_streaming("ecs_task")
            stream_manager.emit_cloudwatch_ready("ecs_task")
        
        thread = threading.Thread(target=delayed_start, daemon=True)
        thread.start()


def _post_destroy_cleanup(deployment_id: str, region: str) -> Dict[str, Any]:
    """
    Perform post-destroy cleanup sweep.
    
    Args:
        deployment_id: Deployment ID
        region: AWS region
        
    Returns:
        Cleanup results
    """
    cleanup_results = {
        "ssm_deleted": 0,
        "log_groups_deleted": 0,
        "tagged_resources_found": 0,
        "tagged_resources_removed": 0,
        "tagged_resources_failed": 0
    }
    
    try:
        # Delete SSM parameters
        try:
            delete_parameters(deployment_id, region)
            cleanup_results["ssm_deleted"] = 1
        except Exception as e:
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": f"SSM cleanup failed: {e}",
                "hint": "SSM parameters may need manual cleanup"
            })
        
        # Delete CloudWatch log groups
        try:
            import boto3
            logs = boto3.client('logs', region_name=region)
            log_group_name = f"/arvo/{deployment_id}"
            
            try:
                logs.delete_log_group(logGroupName=log_group_name)
                cleanup_results["log_groups_deleted"] = 1
            except logs.exceptions.ResourceNotFoundException:
                # Log group doesn't exist, that's fine
                pass
        except Exception as e:
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": f"CloudWatch logs cleanup failed: {e}",
                "hint": "Log groups may need manual cleanup"
            })
        
        # Scan for tagged resources
        try:
            found_resources = list_tagged_resources(region, deployment_id)
            cleanup_results["tagged_resources_found"] = len(found_resources)
            
            if found_resources:
                emit_event(deployment_id, EventTypes.GC_SCAN, {
                    "remaining": len(found_resources),
                    "resources": [{"service": r.service, "arn_or_id": r.arn_or_id} for r in found_resources]
                })
                
                # Attempt to clean up leftover resources
                removed, failed = nuke_if_leftovers(found_resources)
                cleanup_results["tagged_resources_removed"] = removed
                cleanup_results["tagged_resources_failed"] = failed
                
                emit_event(deployment_id, EventTypes.GC_CLEANED, {
                    "removed": removed,
                    "failed": failed
                })
        
        except Exception as e:
            emit_event(deployment_id, EventTypes.ERROR, {
                "reason": f"Resource sweep failed: {e}",
                "hint": "Some resources may need manual cleanup"
            })
    
    except Exception as e:
        emit_event(deployment_id, EventTypes.ERROR, {
            "reason": f"Cleanup sweep failed: {e}",
            "hint": "Manual cleanup may be required"
        })
    
    return cleanup_results
