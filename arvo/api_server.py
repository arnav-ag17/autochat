"""
Backend API Server for Arvo Autodeployment System
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import uuid
from datetime import datetime

from .complete_llm_deploy import deploy_with_complete_llm_system
from .robust_llm import ComprehensiveNLP, ComprehensiveRepositoryAnalyzer

app = FastAPI(
    title="Arvo Autodeployment API",
    description="AI-Powered Application Deployment System",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for deployment status (in production, use Redis or database)
deployment_status = {}


class DeployRequest(BaseModel):
    instructions: str
    repo_url: str
    region: Optional[str] = "us-west-2"


class AnalyzeRequest(BaseModel):
    instructions: str


class InspectRequest(BaseModel):
    repo_url: str


class DeployResponse(BaseModel):
    deployment_id: str
    status: str
    message: str
    application_url: Optional[str] = None
    features: Optional[list] = None


class AnalyzeResponse(BaseModel):
    requirements: Dict[str, Any]
    summary: Dict[str, Any]


class InspectResponse(BaseModel):
    analysis: Dict[str, Any]
    summary: Dict[str, Any]


class StatusResponse(BaseModel):
    deployment_id: str
    status: str
    progress: Optional[str] = None
    application_url: Optional[str] = None
    error: Optional[str] = None
    features: Optional[list] = None


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Arvo Autodeployment API",
        "version": "1.0.0",
        "description": "AI-Powered Application Deployment System",
        "endpoints": {
            "deploy": "/deploy",
            "analyze": "/analyze", 
            "inspect": "/inspect",
            "status": "/status/{deployment_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/deploy", response_model=DeployResponse)
async def deploy_application(request: DeployRequest, background_tasks: BackgroundTasks):
    """Deploy an application using natural language instructions."""
    
    deployment_id = f"d-{int(datetime.now().timestamp())}-{str(uuid.uuid4())[:8]}"
    
    # Initialize deployment status
    deployment_status[deployment_id] = {
        "status": "starting",
        "progress": "Initializing deployment...",
        "timestamp": datetime.now().isoformat(),
        "instructions": request.instructions,
        "repo_url": request.repo_url,
        "region": request.region
    }
    
    # Start deployment in background
    background_tasks.add_task(
        run_deployment, 
        deployment_id, 
        request.instructions, 
        request.repo_url, 
        request.region
    )
    
    return DeployResponse(
        deployment_id=deployment_id,
        status="started",
        message="Deployment started successfully. Use /status/{deployment_id} to check progress."
    )


async def run_deployment(deployment_id: str, instructions: str, repo_url: str, region: str):
    """Run deployment in background."""
    try:
        # Update status
        deployment_status[deployment_id].update({
            "status": "analyzing",
            "progress": "Analyzing requirements and repository..."
        })
        
        # Run deployment
        result = deploy_with_complete_llm_system(instructions, repo_url, region)
        
        # Update final status
        if result["status"] == "success":
            deployment_status[deployment_id].update({
                "status": "completed",
                "progress": "Deployment completed successfully",
                "application_url": result["application_url"],
                "features": result.get("deployment_features", []),
                "terraform_files": result.get("terraform_files", []),
                "llm_requirements": result.get("llm_requirements", {}),
                "llm_analysis": result.get("llm_analysis", {})
            })
        else:
            deployment_status[deployment_id].update({
                "status": "failed",
                "progress": "Deployment failed",
                "error": result.get("error", "Unknown error")
            })
            
    except Exception as e:
        deployment_status[deployment_id].update({
            "status": "failed",
            "progress": "Deployment failed with exception",
            "error": str(e)
        })


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_requirements(request: AnalyzeRequest):
    """Analyze deployment requirements from natural language."""
    
    try:
        nlp = ComprehensiveNLP()
        requirements = nlp.extract_deployment_requirements(request.instructions)
        
        # Create summary
        infra = requirements.get("infrastructure_requirements", {})
        app = requirements.get("application_requirements", {})
        db = requirements.get("database_requirements", {})
        security = requirements.get("security_requirements", {})
        networking = requirements.get("networking", {})
        monitoring = requirements.get("monitoring_logging", {})
        
        summary = {
            "cloud_provider": infra.get("cloud_provider", "aws"),
            "infrastructure_type": infra.get("infrastructure_type", "vm"),
            "instance_type": infra.get("instance_type", "t2.micro"),
            "region": infra.get("region", "us-west-2"),
            "framework": app.get("framework", "unknown"),
            "port": app.get("port", 5000),
            "database": db.get("database_type", "none"),
            "ssl_enabled": security.get("ssl_enabled", False),
            "load_balancer": networking.get("load_balancer", False),
            "monitoring": monitoring.get("monitoring_enabled", False),
            "auto_scaling": infra.get("auto_scaling", {}).get("enabled", False)
        }
        
        return AnalyzeResponse(
            requirements=requirements,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/inspect", response_model=InspectResponse)
async def inspect_repository(request: InspectRequest):
    """Inspect a repository without deploying."""
    
    try:
        analyzer = ComprehensiveRepositoryAnalyzer()
        analysis = analyzer.analyze_repository(request.repo_url)
        
        # Create summary
        app_class = analysis.get("Application Classification", {})
        tech_stack = analysis.get("Technology Stack", {})
        build_deploy = analysis.get("Build & Deployment", {})
        deps = analysis.get("Dependencies & Requirements", {})
        
        summary = {
            "app_type": app_class.get("application_type", "unknown"),
            "framework": app_class.get("framework", "unknown"),
            "runtime": app_class.get("primary_language", "unknown"),
            "build_required": build_deploy.get("build_required", False),
            "dependencies_count": len(deps.get("dependencies", [])),
            "start_command": build_deploy.get("start_command", "auto-detect"),
            "main_directory": analysis.get("Application Structure", {}).get("main_directory", ".")
        }
        
        return InspectResponse(
            analysis=analysis,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inspection failed: {str(e)}")


@app.get("/status/{deployment_id}", response_model=StatusResponse)
async def get_deployment_status(deployment_id: str):
    """Get deployment status."""
    
    if deployment_id not in deployment_status:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    status_info = deployment_status[deployment_id]
    
    return StatusResponse(
        deployment_id=deployment_id,
        status=status_info["status"],
        progress=status_info.get("progress"),
        application_url=status_info.get("application_url"),
        error=status_info.get("error"),
        features=status_info.get("features")
    )


@app.get("/deployments")
async def list_deployments():
    """List all deployments."""
    
    deployments = []
    for deployment_id, status_info in deployment_status.items():
        deployments.append({
            "deployment_id": deployment_id,
            "status": status_info["status"],
            "timestamp": status_info["timestamp"],
            "instructions": status_info.get("instructions", ""),
            "repo_url": status_info.get("repo_url", ""),
            "application_url": status_info.get("application_url")
        })
    
    return {"deployments": deployments}


@app.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str):
    """Delete deployment status."""
    
    if deployment_id not in deployment_status:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    del deployment_status[deployment_id]
    return {"message": "Deployment deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
