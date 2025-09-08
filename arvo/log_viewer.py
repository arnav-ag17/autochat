"""
Log viewer for Arvo deployments.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def view_logs(deployment_id: str) -> None:
    """View logs for a specific deployment."""
    log_file = Path(f".arvo/{deployment_id}/logs.ndjson")
    
    if not log_file.exists():
        print(f"❌ No logs found for deployment {deployment_id}")
        return
    
    print(f"📊 Logs for deployment: {deployment_id}")
    print("=" * 60)
    
    with open(log_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                log_entry = json.loads(line.strip())
                timestamp = log_entry.get('ts', 'Unknown')
                log_type = log_entry.get('type', 'UNKNOWN')
                data = log_entry.get('data', {})
                
                # Format timestamp
                if timestamp != 'Unknown':
                    timestamp = timestamp.replace('T', ' ').split('.')[0]
                
                # Color coding for different log types
                if log_type == 'ERROR':
                    print(f"❌ [{timestamp}] {log_type}: {data.get('reason', 'Unknown error')}")
                elif log_type == 'TF_APPLY_DONE':
                    print(f"✅ [{timestamp}] {log_type}: Terraform apply completed")
                elif log_type == 'SMOKE_FAIL':
                    print(f"⚠️  [{timestamp}] {log_type}: {data.get('hint', 'Smoke test failed')}")
                elif log_type == 'NLP_PASS_A':
                    print(f"🧠 [{timestamp}] {log_type}: Extracted requirements")
                elif log_type == 'INFRA_DECISION':
                    print(f"🏗️  [{timestamp}] {log_type}: Infrastructure decision made")
                elif log_type == 'RECIPE_SELECTED':
                    print(f"📋 [{timestamp}] {log_type}: Recipe selected")
                else:
                    print(f"ℹ️  [{timestamp}] {log_type}")
                
                # Show additional details for important events
                if log_type == 'INFRA_DECISION' and 'target' in data:
                    print(f"   Target: {data['target']}")
                    print(f"   Rationale: {', '.join(data.get('rationale', []))}")
                elif log_type == 'RECIPE_SELECTED' and 'name' in data:
                    print(f"   Recipe: {data['name']}")
                    print(f"   Rationale: {', '.join(data.get('rationale', []))}")
                elif log_type == 'ERROR' and 'hint' in data:
                    print(f"   Hint: {data['hint']}")
                
            except json.JSONDecodeError:
                print(f"⚠️  Invalid JSON on line {line_num}: {line.strip()}")
    
    print("\n" + "=" * 60)


def list_deployments() -> None:
    """List all deployments with their status."""
    arvo_dir = Path(".arvo")
    
    if not arvo_dir.exists():
        print("❌ No deployments found")
        return
    
    print("📋 Deployment History")
    print("=" * 80)
    print(f"{'Deployment ID':<25} {'Status':<10} {'Repository':<30}")
    print("-" * 80)
    
    for deployment_dir in sorted(arvo_dir.iterdir()):
        if deployment_dir.is_dir() and deployment_dir.name.startswith('d-'):
            deployment_id = deployment_dir.name
            
            # Try to determine status from logs
            log_file = deployment_dir / "logs.ndjson"
            status = "Unknown"
            
            if log_file.exists():
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        try:
                            last_log = json.loads(lines[-1].strip())
                            if last_log.get('type') == 'TF_APPLY_DONE':
                                status = "Success"
                            elif last_log.get('type') == 'ERROR':
                                status = "Failed"
                            elif last_log.get('type') == 'SMOKE_FAIL':
                                status = "Failed"
                            else:
                                status = "Running"
                        except:
                            status = "Unknown"
            
            # Try to get repository from logs
            repo_url = "Unknown"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            if log_entry.get('type') == 'INIT' and 'repo' in log_entry.get('data', {}):
                                repo_url = log_entry['data']['repo']
                                break
                        except:
                            continue
            
            # Truncate long URLs
            if len(repo_url) > 30:
                repo_url = repo_url[:27] + "..."
            
            print(f"{deployment_id:<25} {status:<10} {repo_url:<30}")


def view_terraform_config(deployment_id: str) -> None:
    """View Terraform configuration for a deployment."""
    main_tf = Path(f".arvo/{deployment_id}/main.tf")
    
    if not main_tf.exists():
        print(f"❌ No Terraform configuration found for deployment {deployment_id}")
        return
    
    print(f"🏗️  Terraform Configuration for: {deployment_id}")
    print("=" * 60)
    
    with open(main_tf, 'r') as f:
        print(f.read())


def view_terraform_outputs(deployment_id: str) -> None:
    """View Terraform outputs for a deployment."""
    outputs_tf = Path(f".arvo/{deployment_id}/outputs.tf")
    
    if not outputs_tf.exists():
        print(f"❌ No Terraform outputs found for deployment {deployment_id}")
        return
    
    print(f"📊 Terraform Outputs for: {deployment_id}")
    print("=" * 60)
    
    with open(outputs_tf, 'r') as f:
        print(f.read())


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Arvo Log Viewer")
        print("=" * 20)
        print("Usage:")
        print("  python -m arvo.log_viewer list                    # List all deployments")
        print("  python -m arvo.log_viewer logs <deployment_id>    # View logs for deployment")
        print("  python -m arvo.log_viewer config <deployment_id>  # View Terraform config")
        print("  python -m arvo.log_viewer outputs <deployment_id> # View Terraform outputs")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_deployments()
    elif command == "logs" and len(sys.argv) > 2:
        view_logs(sys.argv[2])
    elif command == "config" and len(sys.argv) > 2:
        view_terraform_config(sys.argv[2])
    elif command == "outputs" and len(sys.argv) > 2:
        view_terraform_outputs(sys.argv[2])
    else:
        print("❌ Invalid command. Use 'python -m arvo.log_viewer' for help.")


if __name__ == "__main__":
    main()
