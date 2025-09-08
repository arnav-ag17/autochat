"""Main FastAPI application for Arvo REST API."""

import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from ..orchestrator import deploy, destroy
from ..obs.status import StatusDeriver
from ..envman import redact_secrets


# Pydantic models
class DeployRequest(BaseModel):
    instructions: str
    repo: str
    env: Optional[Dict[str, str]] = None
    overrides: Optional[Dict[str, str]] = None
    noninteractive: bool = True


class DeployResponse(BaseModel):
    deployment_id: str
    message: str


class StatusResponse(BaseModel):
    deployment_id: str
    status: str
    public_url: Optional[str] = None
    log_links: Optional[Dict[str, str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    selector_target: Optional[str] = None
    cost_hint: Optional[str] = None


class DestroyResponse(BaseModel):
    ok: bool


class ErrorResponse(BaseModel):
    error: Dict[str, Any]


# Create FastAPI app
app = FastAPI(
    title="Arvo API",
    description="Automated application deployment system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure via UI_ORIGIN env var in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Arvo API is running", "version": "1.0.0"}


@app.post("/deploy", response_model=DeployResponse)
async def deploy_endpoint(request: DeployRequest):
    """Deploy an application."""
    try:
        # Start deployment
        result = deploy(
            instructions=request.instructions,
            repo=request.repo,
            region=request.overrides.get('region', 'us-west-2') if request.overrides else 'us-west-2',
            user_tags=request.overrides or {}
        )
        
        deployment_id = result.get('deployment_id')
        if not deployment_id:
            raise HTTPException(status_code=500, detail="Failed to create deployment")
        
        return DeployResponse(
            deployment_id=deployment_id,
            message="Deployment started"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "deploy_failed",
                "message": str(e),
                "hint": "Check your repository URL and AWS credentials"
            }
        )


@app.get("/deploy/{deployment_id}/status", response_model=StatusResponse)
async def get_status(deployment_id: str):
    """Get deployment status."""
    try:
        # Read deployment logs to derive status
        logs_dir = Path(f".arvo/{deployment_id}")
        if not logs_dir.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "deployment_not_found",
                    "message": f"Deployment {deployment_id} not found",
                    "hint": "Check the deployment ID"
                }
            )
        
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
        
        return StatusResponse(
            deployment_id=deployment_id,
            status=status_info.get('status', 'unknown'),
            public_url=status_info.get('public_url'),
            log_links=status_info.get('log_links'),
            created_at=status_info.get('created_at'),
            updated_at=status_info.get('updated_at'),
            selector_target=status_info.get('selector_target'),
            cost_hint=status_info.get('cost_hint')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "status_check_failed",
                "message": str(e),
                "hint": "Try again later"
            }
        )


@app.get("/deploy/{deployment_id}/events")
async def stream_events(deployment_id: str):
    """Stream deployment events via Server-Sent Events."""
    try:
        logs_dir = Path(f".arvo/{deployment_id}")
        if not logs_dir.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "deployment_not_found",
                    "message": f"Deployment {deployment_id} not found"
                }
            )
        
        events_file = logs_dir / "logs.ndjson"
        if not events_file.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "no_events",
                    "message": "No events available yet"
                }
            )
        
        async def event_generator():
            """Generate SSE events."""
            last_size = 0
            
            # Send existing events
            with open(events_file) as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        # Redact secrets
                        if 'message' in event:
                            event['message'] = redact_secrets(event['message'])
                        yield f"data: {json.dumps(event)}\n\n"
                    except json.JSONDecodeError:
                        continue
                last_size = events_file.stat().st_size
            
            # Stream new events
            while True:
                try:
                    current_size = events_file.stat().st_size
                    if current_size > last_size:
                        with open(events_file) as f:
                            f.seek(last_size)
                            for line in f:
                                try:
                                    event = json.loads(line.strip())
                                    # Redact secrets
                                    if 'message' in event:
                                        event['message'] = redact_secrets(event['message'])
                                    yield f"data: {json.dumps(event)}\n\n"
                                except json.JSONDecodeError:
                                    continue
                        last_size = current_size
                    
                    # Send heartbeat every 15 seconds
                    yield f"data: {json.dumps({'type': 'HEARTBEAT', 'timestamp': time.time()})}\n\n"
                    
                    import asyncio
                    await asyncio.sleep(15)
                    
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'ERROR', 'message': str(e)})}\n\n"
                    break
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "stream_failed",
                "message": str(e),
                "hint": "Try again later"
            }
        )


@app.post("/deploy/{deployment_id}/destroy", response_model=DestroyResponse)
async def destroy_endpoint(deployment_id: str):
    """Destroy a deployment."""
    try:
        result = destroy(deployment_id)
        
        if result.get('status') == 'success':
            return DestroyResponse(ok=True)
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "destroy_failed",
                    "message": result.get('error', 'Unknown error'),
                    "hint": "Check deployment status and try again"
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "destroy_failed",
                "message": str(e),
                "hint": "Check deployment ID and try again"
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return {
        "error": exc.detail
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler."""
    return {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred",
            "hint": "Please try again later"
        }
    }


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
