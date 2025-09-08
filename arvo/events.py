"""
Event logging utilities for NDJSON format.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .state import get_deployment_dir


def emit_event(deployment_id: str, event_type: str, data: Dict[str, Any]) -> None:
    """
    Emit an event to the deployment's logs.ndjson file.
    
    Args:
        deployment_id: Deployment ID
        event_type: Event type (e.g., "INIT", "TF_PLAN", "ERROR")
        data: Event data
    """
    deployment_dir = get_deployment_dir(deployment_id)
    logs_file = deployment_dir / "logs.ndjson"
    
    event = {
        "ts": datetime.now().isoformat(),
        "type": event_type,
        "data": data
    }
    
    with open(logs_file, "a") as f:
        f.write(json.dumps(event) + "\n")
        f.flush()  # Ensure immediate write


def read_events(deployment_id: str) -> list[Dict[str, Any]]:
    """
    Read all events from a deployment's logs.ndjson file.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        List of events
    """
    deployment_dir = get_deployment_dir(deployment_id)
    logs_file = deployment_dir / "logs.ndjson"
    
    if not logs_file.exists():
        return []
    
    events = []
    with open(logs_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
    
    return events


def get_last_event(deployment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the last event from a deployment's logs.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Last event or None if no events
    """
    events = read_events(deployment_id)
    return events[-1] if events else None


def get_status_from_events(deployment_id: str) -> str:
    """
    Determine deployment status from events.
    
    Args:
        deployment_id: Deployment ID
        
    Returns:
        Status string
    """
    last_event = get_last_event(deployment_id)
    if not last_event:
        return "unknown"
    
    event_type = last_event.get("type", "")
    
    # Map event types to status
    status_map = {
        "INIT": "queued",
        "TF_INIT": "init",
        "TF_PLAN": "tf_init",
        "TF_APPLY_START": "tf_plan",
        "TF_APPLY_DONE": "tf_apply",
        "BOOTSTRAP_WAIT": "bootstrapping",
        "VERIFY_OK": "verifying",
        "DONE": "healthy",
        "ERROR": "failed",
        "DESTROY_START": "destroying",
        "DESTROY_DONE": "destroyed"
    }
    
    return status_map.get(event_type, "unknown")


def tail_events(deployment_id: str, follow: bool = False):
    """
    Generator that yields new events as they're written.
    
    Args:
        deployment_id: Deployment ID
        follow: If True, continue watching for new events
        
    Yields:
        Event dictionaries
    """
    deployment_dir = get_deployment_dir(deployment_id)
    logs_file = deployment_dir / "logs.ndjson"
    
    if not logs_file.exists():
        return
    
    # Read existing events first
    with open(logs_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    event = json.loads(line)
                    yield event
                except json.JSONDecodeError:
                    continue
    
    if not follow:
        return
    
    # Watch for new events
    import time
    last_size = logs_file.stat().st_size
    
    while True:
        try:
            current_size = logs_file.stat().st_size
            if current_size > last_size:
                with open(logs_file, "r") as f:
                    f.seek(last_size)
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                event = json.loads(line)
                                yield event
                            except json.JSONDecodeError:
                                continue
                last_size = current_size
            time.sleep(0.1)
        except (FileNotFoundError, KeyboardInterrupt):
            break


# Predefined event types for consistency
class EventTypes:
    INIT = "INIT"
    TF_INIT = "TF_INIT"
    TF_PLAN = "TF_PLAN"
    TF_APPLY_START = "TF_APPLY_START"
    TF_APPLY_LINE = "TF_APPLY_LINE"
    TF_APPLY_DONE = "TF_APPLY_DONE"
    BOOTSTRAP_WAIT = "BOOTSTRAP_WAIT"
    VERIFY_OK = "VERIFY_OK"
    DONE = "DONE"
    ERROR = "ERROR"
    DESTROY_START = "DESTROY_START"
    DESTROY_DONE = "DESTROY_DONE"
    INFRA_DECISION = "INFRA_DECISION"
    PATCH_APPLIED = "PATCH_APPLIED"
    # Observability events
    OBS_ATTACH = "OBS_ATTACH"
    OBS_LINE = "OBS_LINE"
    OBS_CWL_READY = "OBS_CWL_READY"
    FAILURE_DETECTED = "FAILURE_DETECTED"
    DONE_WITH_LOGS = "DONE_WITH_LOGS"
    # Tagging and cleanup events
    TAGS_APPLIED = "TAGS_APPLIED"
    COST_HINT = "COST_HINT"
    GC_SCAN = "GC_SCAN"
    GC_CLEANED = "GC_CLEANED"
    # TTL events
    TTL_SCHEDULED = "TTL_SCHEDULED"
    TTL_DESTROY_START = "TTL_DESTROY_START"
    TTL_DESTROY_DONE = "TTL_DESTROY_DONE"
    # Recipe events
    RECIPE_SELECTED = "RECIPE_SELECTED"
    # Smoke test events
    SMOKE_ATTEMPT = "SMOKE_ATTEMPT"
    SMOKE_OK = "SMOKE_OK"
    SMOKE_FAIL = "SMOKE_FAIL"
    # NLP events
    NLP_PASS_A = "NLP_PASS_A"
    NLP_PASS_B = "NLP_PASS_B"
    NLP_OVERRIDES = "NLP_OVERRIDES"
