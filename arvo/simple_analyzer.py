"""
Simple repository analyzer for detecting application type and dependencies.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any


def _is_framework_repository(root_path: Path) -> bool:
    """Check if this is a framework repository (not an application)."""
    # Only reject if it's clearly a framework repository
    framework_names = ["flask", "django", "fastapi", "express", "next.js", "react"]
    repo_name = root_path.name.lower()
    
    # If the repo name contains framework names, it's likely a framework
    if any(fw in repo_name for fw in framework_names):
        return True
    
    # Check for strong framework indicators
    strong_indicators = ["setup.py", "pyproject.toml", "tox.ini"]
    strong_count = sum(1 for indicator in strong_indicators 
                      if (root_path / indicator).exists())
    
    # Only reject if it has strong indicators AND no main app
    has_main_app = any((root_path / f).exists() for f in ["app.py", "main.py", "server.py", "run.py", "manage.py"])
    
    return strong_count >= 2 and not has_main_app


def analyze_repository(repo_path: str) -> Dict[str, Any]:
    """
    Analyze repository to detect application type and dependencies.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "runtime": "unknown",
        "framework": "unknown",
        "app_path": ".",
        "port": 8080,
        "start_command": None,
        "dependencies": [],
        "needs_build": False,
        "build_command": None,
        "health_path": "/",
        "warnings": [],
        "rationale": []
    }
    
    root_path = Path(repo_path)
    
    # Check for Python applications
    python_result = _analyze_python_app(root_path)
    if python_result["runtime"]:
        analysis.update(python_result)
        return analysis
    
    # Check for Node.js applications
    node_result = _analyze_node_app(root_path)
    if node_result["runtime"]:
        analysis.update(node_result)
        return analysis
    
    # Check for static applications
    static_result = _analyze_static_app(root_path)
    if static_result["runtime"]:
        analysis.update(static_result)
        return analysis
    
    # Default fallback
    analysis["runtime"] = "python"
    analysis["framework"] = "flask"
    analysis["rationale"].append("No specific framework detected, defaulting to Flask")
    
    return analysis


def _analyze_python_app(root_path: Path) -> Dict[str, Any]:
    """Analyze Python application."""
    result = {"runtime": None}
    
    # Look for Python files and requirements
    python_files = list(root_path.rglob("*.py"))
    requirements_files = list(root_path.rglob("requirements.txt"))
    pyproject_files = list(root_path.rglob("pyproject.toml"))
    
    if not python_files and not requirements_files and not pyproject_files:
        return result
    
    # Skip framework repositories (not actual applications)
    if _is_framework_repository(root_path):
        return result
    
    result["runtime"] = "python"
    result["rationale"] = ["Found Python files or requirements"]
    
    # Determine app path (look for common subdirectories)
    app_path = root_path
    for subdir in ["app", "src", "application", "web", "backend"]:
        subdir_path = root_path / subdir
        if subdir_path.exists() and (subdir_path / "requirements.txt").exists():
            app_path = subdir_path
            result["app_path"] = str(app_path.relative_to(root_path))
            result["rationale"].append(f"Found Python app in {subdir}/ subdirectory")
            break
    
    # Read requirements
    requirements_path = app_path / "requirements.txt"
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            requirements = f.read().strip().split('\n')
            result["dependencies"] = [req.strip() for req in requirements if req.strip()]
    
    # Detect framework and find entry point
    entry_point = None
    for py_file in app_path.rglob("*.py"):
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
                if re.search(r'from\s+flask\s+import|Flask\(', content):
                    result["framework"] = "flask"
                    result["port"] = 5000
                    # Find the actual entry point file
                    if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', content) and 'app.run(' in content:
                        entry_point = py_file.name
                    result["start_command"] = f"python {entry_point or 'app.py'}"
                    result["rationale"].append("Detected Flask application")
                    break
                elif re.search(r'from\s+fastapi\s+import|FastAPI\(', content):
                    result["framework"] = "fastapi"
                    result["port"] = 8000
                    # Find the actual entry point file
                    if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', content):
                        entry_point = py_file.name
                    result["start_command"] = f"uvicorn {entry_point or 'main.py'}:app --host 0.0.0.0 --port 8080"
                    result["rationale"].append("Detected FastAPI application")
                    break
                elif re.search(r'django|manage\.py', content) or (py_file.name == "manage.py"):
                    result["framework"] = "django"
                    result["port"] = 8000
                    result["start_command"] = "python manage.py runserver 0.0.0.0:8080"
                    result["rationale"].append("Detected Django application")
                    break
        except Exception:
            continue
    
    # Default Python settings
    if not result.get("framework"):
        result["framework"] = "flask"
        result["port"] = 5000
        result["start_command"] = "python app.py"
        result["rationale"].append("Python app detected, defaulting to Flask")
    
    return result


def _analyze_node_app(root_path: Path) -> Dict[str, Any]:
    """Analyze Node.js application."""
    result = {"runtime": None}
    
    package_json_files = list(root_path.rglob("package.json"))
    if not package_json_files:
        return result
    
    # Skip framework repositories (not actual applications)
    if _is_framework_repository(root_path):
        return result
    
    result["runtime"] = "node"
    result["rationale"] = ["Found package.json"]
    
    # Read package.json
    package_json_path = package_json_files[0]
    try:
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
            
        result["app_path"] = str(package_json_path.parent.relative_to(root_path))
        result["dependencies"] = list(package_data.get("dependencies", {}).keys())
        
        # Detect framework
        dependencies = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
        scripts = package_data.get("scripts", {})
        
        # Find the main entry point
        main_file = package_data.get("main", "index.js")
        
        if "next" in dependencies:
            result["framework"] = "nextjs"
            result["port"] = 3000
            result["needs_build"] = True
            result["build_command"] = scripts.get("build", "npm run build")
            result["start_command"] = scripts.get("start", "next start")
            result["rationale"].append("Detected Next.js application")
        elif "express" in dependencies:
            result["framework"] = "express"
            result["port"] = 3000
            result["start_command"] = scripts.get("start", f"node {main_file}")
            result["rationale"].append("Detected Express application")
        elif "react" in dependencies and "build" in scripts:
            result["framework"] = "react"
            result["port"] = 3000
            result["needs_build"] = True
            result["build_command"] = scripts.get("build", "npm run build")
            result["start_command"] = "serve -s build"
            result["rationale"].append("Detected React application")
        else:
            result["framework"] = "express"
            result["port"] = 3000
            result["start_command"] = f"node {main_file}"
            result["rationale"].append("Node.js app detected, defaulting to Express")
            
    except Exception as e:
        result["warnings"].append(f"Error reading package.json: {e}")
        result["framework"] = "express"
        result["port"] = 3000
        result["start_command"] = "node index.js"
    
    return result


def _analyze_static_app(root_path: Path) -> Dict[str, Any]:
    """Analyze static application."""
    result = {"runtime": None}
    
    # Look for static files
    static_files = list(root_path.rglob("index.html"))
    if not static_files:
        return result
    
    result["runtime"] = "static"
    result["framework"] = "static"
    result["port"] = 80
    result["start_command"] = "serve -s ."
    result["rationale"] = ["Found static HTML files"]
    
    # Find the root of static files
    for html_file in static_files:
        parent = html_file.parent
        if parent.name in ["dist", "build", "public", "static"]:
            result["app_path"] = str(parent.relative_to(root_path))
        else:
            result["app_path"] = "."
        break
    
    return result
