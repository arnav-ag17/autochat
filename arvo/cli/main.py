"""Main CLI entrypoint for Arvo."""

import json
import sys
import time
from typing import Dict, Any, Optional
import click
from pathlib import Path

from ..simple_deploy import deploy, destroy
from ..obs.status import StatusDeriver
from ..obs.diag import DiagnosticReporter
from ..envman import redact_secrets


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output machine-readable JSON')
@click.pass_context
def main(ctx, output_json):
    """Arvo - Automated application deployment system."""
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json


def _json_output(data: Dict[str, Any]) -> None:
    """Output data as JSON."""
    print(json.dumps(data, indent=None))


def _human_output(message: str) -> None:
    """Output human-readable message."""
    if not click.get_current_context().obj.get('json', False):
        click.echo(message)


@main.command()
@click.option('--instructions', required=True, help='Deployment instructions')
@click.option('--repo', required=True, help='Repository URL or local path')
@click.option('--env-json', help='Environment variables JSON file')
@click.option('--overrides', multiple=True, help='Override key=value pairs')
@click.option('--region', default='us-west-2', help='AWS region')
@click.option('--quiet', is_flag=True, help='Suppress event streaming')
@click.option('--json', 'output_json', is_flag=True, help='Output machine-readable JSON')
@click.pass_context
def deploy_cmd(ctx, instructions, repo, env_json, overrides, region, quiet, output_json):
    """Deploy an application."""
    try:
        # Parse environment variables
        env_vars = {}
        if env_json:
            env_file = Path(env_json)
            if env_file.exists():
                with open(env_file) as f:
                    env_vars = json.load(f)
        
        # Parse overrides
        override_dict = {}
        for override in overrides:
            if '=' in override:
                key, value = override.split('=', 1)
                override_dict[key] = value
        
        # Start deployment
        start_time = time.time()
        result = deploy(
            instructions=instructions,
            repo=repo,
            region=region,
            user_tags=override_dict
        )
        
        deployment_id = result.get('deployment_id')
        status = result.get('status', 'unknown')
        
        if output_json:
            _json_output({
                'deployment_id': deployment_id,
                'status': status,
                'region': region,
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start_time))
            })
        else:
            _human_output(f"🚀 Deployment started: {deployment_id}")
            _human_output(f"Status: {status}")
            _human_output(f"Region: {region}")
            
            if not quiet:
                _human_output("\n📊 Streaming events (press Ctrl+C to stop):")
                _stream_events(deployment_id)
        
        # Exit with appropriate code
        if status == 'success':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        error_msg = f"Deployment failed: {str(e)}"
        if output_json:
            _json_output({'error': error_msg})
        else:
            _human_output(f"❌ {error_msg}")
        sys.exit(1)


@main.command()
@click.argument('deployment_id')
@click.option('--json', 'output_json', is_flag=True, help='Output machine-readable JSON')
@click.pass_context
def status(ctx, deployment_id, output_json):
    """Get deployment status."""
    try:
        # Read deployment logs to derive status
        logs_dir = Path(f".arvo/{deployment_id}")
        if not logs_dir.exists():
            error_msg = f"Deployment {deployment_id} not found"
            if output_json:
                _json_output({'error': error_msg})
            else:
                _human_output(f"❌ {error_msg}")
            sys.exit(2)
        
        # Read events and derive status
        events_file = logs_dir / "logs.ndjson"
        events = []
        if events_file.exists():
            with open(events_file) as f:
                for line in f:
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        
        # Derive status
        deriver = StatusDeriver()
        status_info = deriver.derive_status(events)
        
        if output_json:
            _json_output(status_info)
        else:
            _print_status_human(status_info)
            
    except Exception as e:
        error_msg = f"Status check failed: {str(e)}"
        if output_json:
            _json_output({'error': error_msg})
        else:
            _human_output(f"❌ {error_msg}")
        sys.exit(1)


@main.command()
@click.argument('deployment_id')
@click.option('--follow', is_flag=True, help='Follow logs in real-time')
@click.option('--source', type=click.Choice(['tf', 'runtime', 'all']), default='all', help='Log source filter')
@click.option('--json', 'output_json', is_flag=True, help='Output machine-readable JSON')
@click.pass_context
def logs(ctx, deployment_id, follow, source, output_json):
    """View deployment logs."""
    try:
        logs_dir = Path(f".arvo/{deployment_id}")
        if not logs_dir.exists():
            error_msg = f"Deployment {deployment_id} not found"
            if output_json:
                _json_output({'error': error_msg})
            else:
                _human_output(f"❌ {error_msg}")
            sys.exit(2)
        
        events_file = logs_dir / "logs.ndjson"
        if not events_file.exists():
            _human_output("No logs available yet")
            return
        
        if follow:
            _follow_logs(events_file, source, output_json)
        else:
            _show_logs(events_file, source, output_json)
            
    except KeyboardInterrupt:
        _human_output("\n👋 Stopped following logs")
    except Exception as e:
        error_msg = f"Logs failed: {str(e)}"
        if output_json:
            _json_output({'error': error_msg})
        else:
            _human_output(f"❌ {error_msg}")
        sys.exit(1)


@main.command()
@click.argument('deployment_id')
@click.option('--yes', is_flag=True, help='Skip confirmation prompt')
@click.option('--json', 'output_json', is_flag=True, help='Output machine-readable JSON')
@click.pass_context
def destroy_cmd(ctx, deployment_id, yes, output_json):
    """Destroy a deployment."""
    try:
        if not yes:
            if not click.confirm(f"Are you sure you want to destroy deployment {deployment_id}?"):
                _human_output("❌ Destruction cancelled")
                return
        
        _human_output(f"🗑️  Destroying deployment {deployment_id}...")
        
        result = destroy(deployment_id)
        
        if result.get('status') == 'success':
            if output_json:
                _json_output({'status': 'success', 'message': 'Deployment destroyed'})
            else:
                _human_output("✅ Deployment destroyed successfully")
            sys.exit(0)
        else:
            error_msg = result.get('error', 'Unknown error')
            if output_json:
                _json_output({'status': 'failed', 'error': error_msg})
            else:
                _human_output(f"❌ Destruction failed: {error_msg}")
            sys.exit(1)
            
    except Exception as e:
        error_msg = f"Destruction failed: {str(e)}"
        if output_json:
            _json_output({'error': error_msg})
        else:
            _human_output(f"❌ {error_msg}")
        sys.exit(1)


def _stream_events(deployment_id: str) -> None:
    """Stream events for a deployment."""
    logs_dir = Path(f".arvo/{deployment_id}")
    events_file = logs_dir / "logs.ndjson"
    
    if not events_file.exists():
        return
    
    # Read existing events
    with open(events_file) as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                _print_event_human(event)
            except json.JSONDecodeError:
                continue
    
    # Follow new events
    try:
        import time
        last_size = events_file.stat().st_size
        
        while True:
            time.sleep(1)
            current_size = events_file.stat().st_size
            
            if current_size > last_size:
                with open(events_file) as f:
                    f.seek(last_size)
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            _print_event_human(event)
                        except json.JSONDecodeError:
                            continue
                last_size = current_size
                
    except KeyboardInterrupt:
        pass


def _follow_logs(events_file: Path, source: str, output_json: bool) -> None:
    """Follow logs in real-time."""
    import time
    
    last_size = events_file.stat().st_size
    
    # Show existing logs
    with open(events_file) as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if _should_show_event(event, source):
                    if output_json:
                        _json_output(event)
                    else:
                        _print_event_human(event)
            except json.JSONDecodeError:
                continue
    
    # Follow new logs
    while True:
        time.sleep(1)
        current_size = events_file.stat().st_size
        
        if current_size > last_size:
            with open(events_file) as f:
                f.seek(last_size)
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if _should_show_event(event, source):
                            if output_json:
                                _json_output(event)
                            else:
                                _print_event_human(event)
                    except json.JSONDecodeError:
                        continue
            last_size = current_size


def _show_logs(events_file: Path, source: str, output_json: bool) -> None:
    """Show existing logs."""
    with open(events_file) as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if _should_show_event(event, source):
                    if output_json:
                        _json_output(event)
                    else:
                        _print_event_human(event)
            except json.JSONDecodeError:
                continue


def _should_show_event(event: Dict[str, Any], source: str) -> bool:
    """Check if event should be shown based on source filter."""
    if source == 'all':
        return True
    
    event_type = event.get('type', '')
    
    if source == 'tf':
        return any(event_type.startswith(prefix) for prefix in ['TF_', 'TERRAFORM_'])
    elif source == 'runtime':
        return any(event_type.startswith(prefix) for prefix in ['OBS_', 'SMOKE_', 'RECIPE_'])
    
    return False


def _print_event_human(event: Dict[str, Any]) -> None:
    """Print event in human-readable format."""
    event_type = event.get('type', 'UNKNOWN')
    timestamp = event.get('timestamp', '')
    message = event.get('message', '')
    
    # Redact secrets
    if message:
        message = redact_secrets(message)
    
    # Format timestamp
    if timestamp:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M:%S')
        except:
            time_str = timestamp
    else:
        time_str = ''
    
    # Color coding
    if event_type in ['TF_APPLY_DONE', 'VERIFY_OK', 'DONE_WITH_LOGS']:
        color = 'green'
    elif event_type in ['FAILURE_DETECTED', 'TF_APPLY_ERROR', 'VERIFY_FAIL']:
        color = 'red'
    elif event_type.startswith('TF_'):
        color = 'blue'
    elif event_type.startswith('OBS_'):
        color = 'yellow'
    else:
        color = 'white'
    
    click.echo(f"[{time_str}] {click.style(event_type, fg=color)}: {message}")


def _print_status_human(status_info: Dict[str, Any]) -> None:
    """Print status in human-readable format."""
    deployment_id = status_info.get('deployment_id', 'unknown')
    status = status_info.get('status', 'unknown')
    public_url = status_info.get('public_url')
    log_links = status_info.get('log_links', {})
    
    click.echo(f"📊 Deployment: {deployment_id}")
    click.echo(f"Status: {click.style(status, fg='green' if status == 'healthy' else 'red')}")
    
    if public_url:
        click.echo(f"🌐 Public URL: {click.style(public_url, fg='blue', underline=True)}")
    
    if log_links:
        click.echo("📋 Log Links:")
        for name, url in log_links.items():
            click.echo(f"  {name}: {click.style(url, fg='blue', underline=True)}")
    
    # Show recent events
    recent_events = status_info.get('recent_events', [])
    if recent_events:
        click.echo("\n📝 Recent Events:")
        for event in recent_events[-5:]:  # Last 5 events
            event_type = event.get('type', 'UNKNOWN')
            message = event.get('message', '')
            click.echo(f"  {event_type}: {message}")


if __name__ == '__main__':
    main()
