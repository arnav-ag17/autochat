from __future__ import annotations

from pathlib import Path
from typing import List

from .spec import DeploymentSpec
from .detect_common import find_manifests, parse_env_requirements, find_localhost_refs, infer_health_path
from .detect_python import detect_python
from .detect_node import detect_node
from .detect_container import detect_container
from .detect_static import detect_static


def resolve_spec(app_root: str) -> DeploymentSpec:
    manifests = find_manifests(app_root)
    env_keys, env_example_path = parse_env_requirements(app_root)
    localhost_refs, loopback_binds = find_localhost_refs(app_root)
    health = infer_health_path(app_root)

    py = detect_python(app_root)
    nd = detect_node(app_root)
    ct = detect_container(app_root)
    st = detect_static(app_root)

    runtime = "unknown"
    framework = None
    start_command = None
    port = None
    needs_build = False
    build_command = None
    static_assets = None
    db_required = False
    containerized = bool(ct.get("containerized"))
    multi_service = bool(ct.get("multi_service"))
    rationale: List[str] = []

    # Priority resolution
    if containerized:
        runtime = ct.get("runtime") or "container"
        rationale.append("Containerized project detected (Dockerfile/compose)")
    elif nd.get("runtime") == "node":
        runtime = "node"
        framework = nd.get("framework")
        start_command = nd.get("start_command")
        port = nd.get("port")
        needs_build = bool(nd.get("needs_build"))
        build_command = nd.get("build_command")
        static_assets = nd.get("static_assets")
        db_required = bool(nd.get("db_required"))
        rationale.extend(nd.get("rationale", []))
    elif py.get("runtime") == "python":
        runtime = "python"
        framework = py.get("framework")
        start_command = py.get("start_command")
        port = py.get("port")
        db_required = bool(py.get("db_required"))
        rationale.extend(py.get("rationale", []))
    elif st.get("runtime") == "static":
        runtime = "static"
        framework = st.get("framework")
        needs_build = bool(st.get("needs_build"))
        build_command = st.get("build_command")
        static_assets = st.get("static_assets")
        rationale.extend(st.get("rationale", []))

    warnings: List[str] = []
    if localhost_refs:
        warnings.append("Found localhost references that may need rewriting at deploy time")
    if loopback_binds:
        warnings.append("Found explicit 127.0.0.1 binds; these will be rewritten to 0.0.0.0")

    # Use the detected app_path from the runtime detector, fallback to app_root
    detected_app_path = py.get("app_path") or nd.get("app_path") or st.get("app_path") or app_root
    
    return DeploymentSpec(
        app_path=str(Path(detected_app_path).resolve()),
        runtime=runtime,
        framework=framework,
        containerized=containerized,
        multi_service=multi_service,
        start_command=start_command,
        port=port,
        health_path=health,
        needs_build=needs_build,
        build_command=build_command,
        static_assets=static_assets,
        db_required=db_required,
        env_required=env_keys,
        env_example_path=env_example_path,
        localhost_refs=localhost_refs,
        loopback_binds=loopback_binds,
        warnings=warnings,
        rationale=rationale,
        manifests=manifests,
    )
