"""
FastAPI REST service for deployment orchestration.
"""

import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from .orchestrator import deploy, status, outputs, logs, destroy
from .events import tail_events, read_events
from .state import list_deployments
from .obs import CloudWatchLinkBuilder


app = FastAPI(
    title="Arvo Deployment API",
    description="REST API for automated deployment orchestration",
    version="0.1.0"
)


class DeployRequest(BaseModel):
    instructions: str
    repo: str
    region: Optional[str] = "us-west-2"
    user_tags: Optional[Dict[str, str]] = None
    ttl_hours: Optional[int] = None


class DeployResponse(BaseModel):
    deployment_id: str


class StatusResponse(BaseModel):
    deployment_id: str
    status: str
    public_url: Optional[str] = None


class OutputsResponse(BaseModel):
    deployment_id: str
    outputs: Optional[Dict[str, Any]] = None


class DestroyResponse(BaseModel):
    deployment_id: str
    status: str


class GcRequest(BaseModel):
    deployment_id: Optional[str] = None
    auto_confirm: bool = False


class GcResponse(BaseModel):
    found_resources: int
    removed_resources: int
    failed_resources: int
    resources: list


# Background task storage
deployment_tasks: Dict[str, asyncio.Task] = {}


@app.post("/deployments", response_model=DeployResponse)
async def create_deployment(request: DeployRequest, background_tasks: BackgroundTasks):
    """
    Start a new deployment.
    """
    # Start deployment in background
    task = asyncio.create_task(
        asyncio.to_thread(
            deploy,
            request.instructions,
            request.repo,
            request.region
        )
    )
    
    # Get deployment ID from the task (we need to modify deploy to return ID immediately)
    # For now, we'll generate one and store the task
    from .ids import new_deployment_id
    deployment_id = new_deployment_id()
    deployment_tasks[deployment_id] = task
    
    # Start the actual deployment
    background_tasks.add_task(
        _run_deployment,
        deployment_id,
        request.instructions,
        request.repo,
        request.region,
        request.user_tags,
        request.ttl_hours
    )
    
    return DeployResponse(deployment_id=deployment_id)


async def _run_deployment(deployment_id: str, instructions: str, repo: str, region: str, user_tags: Optional[Dict[str, str]] = None, ttl_hours: Optional[int] = None):
    """
    Run deployment in background.
    """
    try:
        result = await asyncio.to_thread(deploy, instructions, repo, region, deployment_id, user_tags, ttl_hours)
        # Clean up task when done
        if deployment_id in deployment_tasks:
            del deployment_tasks[deployment_id]
    except Exception as e:
        # Clean up task on error
        if deployment_id in deployment_tasks:
            del deployment_tasks[deployment_id]
        raise e


@app.get("/deployments/{deployment_id}", response_model=StatusResponse)
async def get_deployment_status(deployment_id: str):
    """
    Get deployment status.
    """
    result = await asyncio.to_thread(status, deployment_id)
    
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return StatusResponse(**result)


@app.get("/deployments/{deployment_id}/outputs", response_model=OutputsResponse)
async def get_deployment_outputs(deployment_id: str):
    """
    Get deployment outputs.
    """
    result = await asyncio.to_thread(outputs, deployment_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return OutputsResponse(deployment_id=deployment_id, outputs=result)


@app.get("/deployments/{deployment_id}/events")
async def stream_deployment_events(deployment_id: str):
    """
    Stream deployment events as Server-Sent Events.
    """
    from .state import deployment_exists
    
    if not deployment_exists(deployment_id):
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    async def event_generator():
        try:
            for event in tail_events(deployment_id, follow=True):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/deployments/{deployment_id}/destroy", response_model=DestroyResponse)
async def destroy_deployment(deployment_id: str, background_tasks: BackgroundTasks, force: bool = False):
    """
    Destroy a deployment.
    """
    # Check if deployment exists
    from .state import deployment_exists
    if not deployment_exists(deployment_id):
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Start destroy in background
    background_tasks.add_task(
        asyncio.to_thread,
        destroy,
        deployment_id,
        force
    )
    
    return DestroyResponse(deployment_id=deployment_id, status="destroying")


@app.get("/deployments/{deployment_id}/runtime-logs")
async def get_runtime_logs(deployment_id: str):
    """
    Get runtime logs information and links.
    """
    from .state import deployment_exists
    
    if not deployment_exists(deployment_id):
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Get deployment outputs to determine log sources
    outputs_result = await asyncio.to_thread(outputs, deployment_id)
    
    if not outputs_result:
        raise HTTPException(status_code=404, detail="Deployment outputs not found")
    
    # Build log links
    region = "us-west-2"  # Default region, could be extracted from outputs
    link_builder = CloudWatchLinkBuilder(region)
    log_links = link_builder.build_log_links(deployment_id, outputs_result)
    
    # Get recent runtime log events
    events = await asyncio.to_thread(read_events, deployment_id)
    runtime_events = [
        event for event in events 
        if event.get("type") in ["OBS_LINE", "FAILURE_DETECTED", "BOOTSTRAP_WAIT", "VERIFY_OK"]
    ]
    
    return {
        "deployment_id": deployment_id,
        "log_group": f"/arvo/{deployment_id}",
        "log_links": log_links,
        "recent_events": runtime_events[-20:],  # Last 20 runtime events
        "tail_command": link_builder.build_tail_command(f"/arvo/{deployment_id}")
    }


@app.get("/deployments")
async def list_all_deployments():
    """
    List all deployments.
    """
    deployment_ids = await asyncio.to_thread(list_deployments)
    
    results = []
    for deployment_id in deployment_ids:
        status_result = await asyncio.to_thread(status, deployment_id)
        results.append(status_result)
    
    return {"deployments": results}


@app.post("/gc", response_model=GcResponse)
async def garbage_collect(request: GcRequest):
    """
    Garbage collect leftover resources.
    """
    from .cleanup import list_tagged_resources, nuke_if_leftovers
    
    if request.deployment_id:
        # GC specific deployment
        found = await asyncio.to_thread(list_tagged_resources, "us-west-2", request.deployment_id)
        if found:
            removed, failed = await asyncio.to_thread(nuke_if_leftovers, found)
        else:
            removed, failed = 0, 0
        
        return GcResponse(
            found_resources=len(found),
            removed_resources=removed,
            failed_resources=failed,
            resources=[{"service": r.service, "arn_or_id": r.arn_or_id, "tags": r.tags} for r in found]
        )
    else:
        # GC all deployments
        from .state import list_deployments
        deployment_ids = await asyncio.to_thread(list_deployments)
        
        total_found = 0
        total_removed = 0
        total_failed = 0
        all_resources = []
        
        for deployment_id in deployment_ids:
            found = await asyncio.to_thread(list_tagged_resources, "us-west-2", deployment_id)
            if found:
                total_found += len(found)
                all_resources.extend([{"service": r.service, "arn_or_id": r.arn_or_id, "tags": r.tags, "deployment_id": deployment_id} for r in found])
                
                if request.auto_confirm:
                    removed, failed = await asyncio.to_thread(nuke_if_leftovers, found)
                    total_removed += removed
                    total_failed += failed
        
        return GcResponse(
            found_resources=total_found,
            removed_resources=total_removed,
            failed_resources=total_failed,
            resources=all_resources
        )


@app.get("/ttl")
async def list_ttl_deployments():
    """
    List all deployments with TTL information.
    """
    from .ttl import list_ttl_deployments
    ttl_deployments = await asyncio.to_thread(list_ttl_deployments)
    return {"ttl_deployments": ttl_deployments}


@app.post("/ttl/run")
async def run_ttl_sweep():
    """
    Run TTL sweep to destroy expired deployments.
    """
    from .ttl import run_ttl_sweep
    result = await asyncio.to_thread(run_ttl_sweep)
    return result


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "service": "arvo-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
