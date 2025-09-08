from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .walk import iter_files, read_text


PY_PORT_DEFAULTS = {
    "flask": 5000,
    "fastapi": 8000,
    "django": 8000,
}


def detect_python(app_root: str) -> Dict:
    res: Dict = {
        "runtime": None,
        "framework": None,
        "start_command": None,
        "port": None,
        "needs_build": False,
        "build_command": None,
        "db_required": False,
        "app_path": app_root,  # Will be updated if subdirectory is found
        "rationale": [],
    }

    root = Path(app_root)
    has_requirements = (root / "requirements.txt").exists()
    has_pyproject = (root / "pyproject.toml").exists()
    has_pipfile = (root / "Pipfile").exists()
    
    # Check for common subdirectory patterns
    app_subdirs = ["app", "src", "application", "web", "backend"]
    actual_app_path = app_root
    
    if not (has_requirements or has_pyproject or has_pipfile):
        # Look for requirements.txt in common subdirectories
        for subdir in app_subdirs:
            subdir_path = root / subdir
            if subdir_path.exists() and (subdir_path / "requirements.txt").exists():
                has_requirements = True
                actual_app_path = str(subdir_path)
                res["app_path"] = actual_app_path
                res["rationale"].append(f"Found Python app in {subdir}/ subdirectory")
                break
    
    if not (has_requirements or has_pyproject or has_pipfile):
        # best-effort: look for .py files
        if not any(str(p).endswith(".py") for p, _ in iter_files(root)):
            return res

    res["runtime"] = "python"

    deps_text = ""
    if has_requirements:
        deps_text = read_text(Path(actual_app_path) / "requirements.txt")
    # Framework detection
    flask_hits: List[str] = []
    fastapi_hits: List[str] = []
    django_hits: List[str] = []

    # Look for Python files in the actual app path
    app_path = Path(actual_app_path)
    for fp, _ in iter_files(app_path):
        if not str(fp).endswith(".py"):
            continue
        text = read_text(fp)
        if not text:
            continue
        if re.search(r"from\s+flask\s+import|Flask\(", text):
            flask_hits.append(str(fp))
        if re.search(r"from\s+fastapi\s+import|FastAPI\(", text):
            fastapi_hits.append(str(fp))
        if "manage.py" in str(fp) or re.search(r"django", text):
            if "manage.py" in str(fp) or re.search(r"INSTALLED_APPS", text):
                django_hits.append(str(fp))

    if django_hits:
        res["framework"] = "django"
        res["port"] = PY_PORT_DEFAULTS["django"]
        res["start_command"] = "python manage.py runserver"
        res["rationale"].append("Detected Django via manage.py/settings hints")
        # DB heuristic
        if "django" in deps_text.lower():
            res["db_required"] = True
    elif fastapi_hits:
        res["framework"] = "fastapi"
        res["port"] = PY_PORT_DEFAULTS["fastapi"]
        # try to infer module containing FastAPI()
        mod = Path(fastapi_hits[0]).with_suffix("").name
        res["start_command"] = f"uvicorn {mod}:app"
        res["rationale"].append("Detected FastAPI via 'FastAPI(' signature")
        # DB heuristic from deps
        if re.search(r"(psycopg2|mysqlclient|pymysql|sqlalchemy|motor|mongoengine|redis|celery)", deps_text, re.I):
            res["db_required"] = True
    elif flask_hits:
        res["framework"] = "flask"
        res["port"] = PY_PORT_DEFAULTS["flask"]
        res["start_command"] = None  # Let recipe handle the proper start command
        res["rationale"].append("Detected Flask via 'from flask import' or 'Flask(' signature")
        if re.search(r"(psycopg2|mysqlclient|pymysql|sqlalchemy|motor|mongoengine|redis|celery)", deps_text, re.I):
            res["db_required"] = True

    return res
