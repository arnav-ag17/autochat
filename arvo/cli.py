"""
Click CLI interface for Arvo deployment orchestration.
This is the legacy CLI - new CLI is in arvo/cli/main.py
"""

import json
import sys
from typing import Optional
import click

from .orchestrator import deploy, status, outputs, logs, destroy
from .events import tail_events, read_events
from .state import list_deployments
from .ids import new_deployment_id, is_valid_deployment_id
from .obs import StatusDeriver, DiagnosticReporter, CloudWatchLinkBuilder
from .tags import parse_user_tags
from .ttl import run_ttl_sweep, list_ttl_deployments
from .cleanup import list_tagged_resources, nuke_if_leftovers


@click.group()
def main():
    """
    Arvo - Automated deployment orchestrator for Terraform-based applications.
    """
    pass


@main.command()
@click.option("--instructions", required=True, help="Deployment instructions")
@click.option("--repo", required=True, help="Repository URL (git or zip)")
@click.option("--region", default="us-west-2", help="AWS region")
@click.option("--id", help="Optional deployment ID")
@click.option("--tag", "tags", multiple=True, help="Tags in format 'key=value' (repeatable)")
@click.option("--ttl-hours", type=int, help="TTL in hours for auto-destroy")
def deploy_cmd(instructions: str, repo: str, region: str, id: Optional[str], tags: tuple, ttl_hours: Optional[int]):
    """
    Deploy an application using Terraform.
    """
    deployment_id = id or new_deployment_id()
    
    # Parse user tags
    user_tags = None
    if tags:
        try:
            user_tags = parse_user_tags(list(tags))
        except ValueError as e:
            click.echo(f"Invalid tag format: {e}", err=True)
            sys.exit(1)
    
    # Stream events to stdout
    def stream_events():
        for event in tail_events(deployment_id, follow=True):
            print(json.dumps(event), flush=True)
    
    # Start event streaming in background
    import threading
    event_thread = threading.Thread(target=stream_events, daemon=True)
    event_thread.start()
    
    try:
        # Run deployment
        result = deploy(instructions, repo, region, deployment_id, user_tags, ttl_hours)
        
        # Print final result as JSON
        print(json.dumps(result), file=sys.stdout)
        
        # Exit with appropriate code
        if result["status"] == "healthy":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\nDeployment cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Deployment failed: {str(e)}", err=True)
        sys.exit(1)


@main.command()
@click.argument("deployment_id")
@click.option("--format", "output_format", type=click.Choice(["json", "human"]), default="human", help="Output format")
def status_cmd(deployment_id: str, output_format: str):
    """
    Get deployment status with comprehensive information.
    """
    if not is_valid_deployment_id(deployment_id):
        click.echo(f"Invalid deployment ID: {deployment_id}", err=True)
        sys.exit(1)
    
    # Get basic status
    result = status(deployment_id)
    
    if output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        # Human-readable format
        click.echo(f"🆔 Deployment ID: {deployment_id}")
        click.echo(f"📊 Status: {result.get('status', 'unknown').upper()}")
        
        if result.get('public_url'):
            click.echo(f"🌐 Public URL: {result['public_url']}")
        
        if result.get('log_links'):
            click.echo("📋 Log Links:")
            for name, url in result['log_links'].items():
                click.echo(f"  • {name}: {url}")
        
        # Show last few events
        events = read_events(deployment_id)
        if events:
            click.echo(f"\n📝 Recent Events (last 5):")
            for event in events[-5:]:
                event_type = event.get('type', 'unknown')
                timestamp = event.get('ts', 'unknown')
                click.echo(f"  • {timestamp}: {event_type}")
                if event.get('data', {}).get('message'):
                    click.echo(f"    {event['data']['message']}")
        
        # Show failure info if failed
        if result.get('status') == 'failed' and result.get('failure_reason'):
            click.echo(f"\n❌ Failure: {result['failure_reason']}")
            if result.get('failure_hint'):
                click.echo(f"💡 Hint: {result['failure_hint']}")


@main.command()
@click.argument("deployment_id")
@click.option("--follow", "-f", is_flag=True, help="Follow logs in real-time")
@click.option("--source", type=click.Choice(["tf", "runtime", "all"]), default="all", help="Filter by log source")
@click.option("--format", "output_format", type=click.Choice(["json", "human"]), default="human", help="Output format")
def logs_cmd(deployment_id: str, follow: bool, source: str, output_format: str):
    """
    Show deployment logs with filtering and formatting options.
    """
    if not is_valid_deployment_id(deployment_id):
        click.echo(f"Invalid deployment ID: {deployment_id}", err=True)
        sys.exit(1)
    
    def filter_event(event, source_filter):
        """Filter events by source."""
        if source_filter == "all":
            return True
        elif source_filter == "tf":
            return event.get("type", "").startswith("TF_")
        elif source_filter == "runtime":
            return event.get("type", "") in ["OBS_LINE", "FAILURE_DETECTED", "BOOTSTRAP_WAIT", "VERIFY_OK"]
        return True
    
    def format_event(event, fmt):
        """Format event for display."""
        if fmt == "json":
            return json.dumps(event)
        else:
            # Human-readable format
            event_type = event.get("type", "unknown")
            timestamp = event.get("ts", "unknown")
            data = event.get("data", {})
            
            if event_type == "OBS_LINE":
                source = data.get("source", "unknown")
                message = data.get("message", "")
                return f"[{timestamp}] {source}: {message}"
            elif event_type == "FAILURE_DETECTED":
                reason = data.get("reason_code", "unknown")
                message = data.get("message", "")
                return f"[{timestamp}] ❌ FAILURE ({reason}): {message}"
            else:
                message = data.get("message", "")
                return f"[{timestamp}] {event_type}: {message}"
    
    if follow:
        # Stream logs in real-time
        try:
            for event in tail_events(deployment_id, follow=True):
                if filter_event(event, source):
                    formatted = format_event(event, output_format)
                    print(formatted, flush=True)
        except KeyboardInterrupt:
            click.echo("\nLog streaming stopped", err=True)
    else:
        # Show all logs
        log_events = logs(deployment_id)
        for event in log_events:
            if filter_event(event, source):
                formatted = format_event(event, output_format)
                print(formatted)


@main.command()
@click.argument("deployment_id")
def outputs_cmd(deployment_id: str):
    """
    Show deployment outputs.
    """
    if not is_valid_deployment_id(deployment_id):
        click.echo(f"Invalid deployment ID: {deployment_id}", err=True)
        sys.exit(1)
    
    result = outputs(deployment_id)
    if result is None:
        click.echo(f"Deployment {deployment_id} not found or no outputs available", err=True)
        sys.exit(1)
    
    print(json.dumps(result, indent=2))


@main.command()
@click.argument("deployment_id")
@click.option("--force", is_flag=True, help="Force destroy without confirmation")
def destroy_cmd(deployment_id: str, force: bool):
    """
    Destroy a deployment.
    """
    if not is_valid_deployment_id(deployment_id):
        click.echo(f"Invalid deployment ID: {deployment_id}", err=True)
        sys.exit(1)
    
    if not force:
        if not click.confirm(f"Are you sure you want to destroy deployment {deployment_id}?"):
            click.echo("Destroy cancelled")
            return
    
    result = destroy(deployment_id)
    print(json.dumps(result, indent=2))
    
    if result["status"] == "destroyed":
        sys.exit(0)
    else:
        sys.exit(1)


@main.command()
def list_cmd():
    """
    List all deployments.
    """
    deployment_ids = list_deployments()
    
    if not deployment_ids:
        click.echo("No deployments found")
        return
    
    results = []
    for deployment_id in deployment_ids:
        status_result = status(deployment_id)
        results.append(status_result)
    
    print(json.dumps(results, indent=2))


@main.command()
@click.option("--all", is_flag=True, help="List all deployments with TTL information")
def ttl_cmd(all: bool):
    """
    Run TTL sweep to destroy expired deployments.
    """
    if all:
        # List all TTL deployments
        ttl_deployments = list_ttl_deployments()
        
        if not ttl_deployments:
            click.echo("No deployments with TTL found")
            return
        
        click.echo("🕒 TTL Deployments:")
        for ttl_data in ttl_deployments:
            deployment_id = ttl_data["deployment_id"]
            ttl_hours = ttl_data["ttl_hours"]
            expires_at = ttl_data["expires_at"]
            exists = ttl_data.get("exists", False)
            expired = ttl_data.get("expired", False)
            
            status_icon = "✅" if exists else "❌"
            expired_icon = "⏰" if expired else "⏳"
            
            click.echo(f"  {status_icon} {expired_icon} {deployment_id}: {ttl_hours}h TTL, expires {expires_at}")
    else:
        # Run TTL sweep
        click.echo("🕒 Running TTL sweep...")
        results = run_ttl_sweep()
        
        click.echo(f"📊 TTL Sweep Results:")
        click.echo(f"  • Total deployments checked: {results['total_checked']}")
        click.echo(f"  • Expired deployments found: {len(results['expired_deployments'])}")
        click.echo(f"  • Successfully destroyed: {results['destroyed_count']}")
        click.echo(f"  • Failed to destroy: {results['failed_count']}")
        
        if results['expired_deployments']:
            click.echo(f"  • Expired deployments: {', '.join(results['expired_deployments'])}")


@main.command()
@click.option("--all", is_flag=True, help="Scan all deployments for leftover resources")
@click.option("--yes", is_flag=True, help="Auto-confirm cleanup without prompting")
def gc_cmd(all: bool, yes: bool):
    """
    Garbage collect leftover resources.
    """
    if all:
        # Scan all deployments
        deployment_ids = list_deployments()
        all_leftovers = {}
        
        for deployment_id in deployment_ids:
            try:
                # Get deployment region
                from .state import read_env_json
                env_data = read_env_json(deployment_id)
                region = env_data.get("region", "us-west-2")
                
                # Find tagged resources
                found_resources = list_tagged_resources(region, deployment_id)
                if found_resources:
                    all_leftovers[deployment_id] = found_resources
            except Exception as e:
                click.echo(f"⚠️  Error scanning {deployment_id}: {e}", err=True)
        
        if not all_leftovers:
            click.echo("✅ No leftover resources found")
            return
        
        click.echo(f"🗑️  Found leftover resources for {len(all_leftovers)} deployments:")
        for deployment_id, resources in all_leftovers.items():
            click.echo(f"  📦 {deployment_id}: {len(resources)} resources")
            for resource in resources:
                click.echo(f"    • {resource.service}: {resource.arn_or_id}")
        
        if yes or click.confirm("Do you want to clean up these resources?"):
            total_removed = 0
            total_failed = 0
            
            for deployment_id, resources in all_leftovers.items():
                click.echo(f"🧹 Cleaning up {deployment_id}...")
                removed, failed = nuke_if_leftovers(resources)
                total_removed += removed
                total_failed += failed
            
            click.echo(f"✅ Cleanup complete: {total_removed} removed, {total_failed} failed")
        else:
            click.echo("❌ Cleanup cancelled")
    else:
        click.echo("Use --all to scan for leftover resources")


@main.command()
@click.argument("deployment_id")
def doctor_cmd(deployment_id: str):
    """
    Run diagnostic analysis on a deployment.
    """
    if not is_valid_deployment_id(deployment_id):
        click.echo(f"Invalid deployment ID: {deployment_id}", err=True)
        sys.exit(1)
    
    # Get events and outputs
    events = read_events(deployment_id)
    outputs_result = outputs(deployment_id)
    
    # Generate diagnostic report
    reporter = DiagnosticReporter()
    report = reporter.generate_report(
        deployment_id=deployment_id,
        events=events,
        outputs=outputs_result
    )
    
    # Display formatted report
    formatted_report = reporter.format_report(report)
    click.echo(formatted_report)


@main.command()
@click.option("--type", "app_type", required=True, 
              type=click.Choice(['flask', 'fastapi', 'django', 'express', 'next', 'docker']),
              help="Type of application to test")
@click.option("--region", default="us-west-2", help="AWS region")
@click.option("--ttl-hours", type=int, default=1, help="TTL in hours for auto-destroy")
def recipes_test(app_type: str, region: str, ttl_hours: int):
    """
    Test a specific recipe type with a fixture application.
    """
    import os
    from pathlib import Path
    
    # Get fixture path
    fixture_dir = Path(__file__).parent.parent / "tests" / "fixtures_runtime"
    app_fixtures = {
        'flask': 'flask_app',
        'fastapi': 'fastapi_app', 
        'django': 'django_app',
        'express': 'express_app',
        'next': 'nextjs_app',
        'docker': 'docker_app'
    }
    
    if app_type not in app_fixtures:
        click.echo(f"Unknown app type: {app_type}", err=True)
        sys.exit(1)
    
    fixture_path = fixture_dir / app_fixtures[app_type]
    if not fixture_path.exists():
        click.echo(f"Fixture not found: {fixture_path}", err=True)
        sys.exit(1)
    
    click.echo(f"Testing {app_type} recipe with fixture: {fixture_path}")
    
    # Deploy the fixture
    try:
        result = deploy(
            instructions=f"Deploy {app_type} test application",
            repo=str(fixture_path),
            region=region,
            ttl_hours=ttl_hours
        )
        
        if result.get("status") == "success":
            click.echo(f"✅ {app_type} recipe test PASSED")
            click.echo(f"Public URL: {result.get('public_url')}")
            click.echo(f"Deployment ID: {result.get('deployment_id')}")
            click.echo(f"Auto-destroy scheduled in {ttl_hours} hour(s)")
        else:
            click.echo(f"❌ {app_type} recipe test FAILED")
            click.echo(f"Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ {app_type} recipe test FAILED with exception: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=7000, help="Port to bind to")
def serve(host: str, port: int):
    """
    Start the REST API server.
    """
    import uvicorn
    from .api import app
    
    click.echo(f"Starting Arvo API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
