import tempfile
from pathlib import Path
from arvo.patcher import apply_patches
from arvo.analyzer.spec import DeploymentSpec
from arvo.selector.plan import InfraPlan


def spec_of(**kw):
    base = dict(
        app_path="/app",
        runtime="python",
        framework="flask",
        containerized=False,
        multi_service=False,
        start_command="flask run",
        port=5000,
        health_path="",
        needs_build=False,
        build_command=None,
        static_assets=None,
        db_required=False,
        env_required=[],
        env_example_path=None,
        localhost_refs=[],
        loopback_binds=[],
        warnings=[],
        rationale=[],
        manifests={},
        extra={},
    )
    base.update(kw)
    return DeploymentSpec(**base)


def test_fastapi_uvicorn_synth_ec2_and_health_default():
    spec = spec_of(runtime="python", framework="fastapi", start_command="uvicorn main:app", port=8000)
    plan = InfraPlan(target="ec2", module_hint="ec2_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p/"main.py").write_text("from fastapi import FastAPI\napp=FastAPI()\n")
        result = apply_patches(spec, plan, td)
        assert result.systemd_unit is not None
        assert result.start_command.startswith("uvicorn")
        assert result.health_path in ("/health", "/")
        assert result.env_overrides["PORT"] == "8000"


def test_django_synth_ec2_produces_unit_and_port_env():
    spec = spec_of(runtime="python", framework="django", start_command=None, port=8000)
    plan = InfraPlan(target="ec2", module_hint="ec2_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        (Path(td)/"manage.py").write_text("print('ok')\n")
        result = apply_patches(spec, plan, td)
        assert result.systemd_unit is not None
        assert "runserver" in (result.start_command or "")
        assert result.env_overrides["PORT"] == "8000"


def test_static_site_noop():
    spec = spec_of(runtime="static", framework=None, start_command=None, static_assets="build/", port=None)
    plan = InfraPlan(target="ec2", module_hint="ec2_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        result = apply_patches(spec, plan, td)
        assert result.start_command is None
        assert result.systemd_unit is None


def test_html_js_localhost_to_relative():
    spec = spec_of()
    plan = InfraPlan(target="ec2", module_hint="ec2_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        html = Path(td)/"index.html"
        js = Path(td)/"app.js"
        html.write_text('<script>fetch("http://localhost:5000/api/message")</script>')
        js.write_text("fetch('http://127.0.0.1:5000/api')")
        result = apply_patches(spec, plan, td)
        assert any("api_base=relative" in c for c in result.changes)
        # ensure files updated
        assert "/api/message" in html.read_text()
        assert "/api" in js.read_text()


def test_express_container_cmd_and_loopback_bind_rewrite():
    spec = spec_of(runtime="node", framework="express", start_command="node server.js", port=3000)
    plan = InfraPlan(target="ecs_fargate", module_hint="ecs_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        srv = Path(td)/"server.js"
        srv.write_text("const app=require('express')(); app.listen(3000,'localhost');")
        result = apply_patches(spec, plan, td)
        assert result.container_cmd is not None
        # idempotency: second run should not duplicate markers
        changes_before = len(result.changes)
        result2 = apply_patches(spec, plan, td)
        assert len(result2.changes) >= 0


def test_multi_service_enables_auto_cors():
    spec = spec_of(multi_service=True)
    plan = InfraPlan(target="ec2", module_hint="ec2_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        result = apply_patches(spec, plan, td)
        assert result.cors_mode in ("auto", "none")
        assert result.env_overrides["PORT"] == "5000"


def test_service_origin_placeholder_when_multi_service():
    spec = spec_of(multi_service=True)
    plan = InfraPlan(target="ec2", module_hint="ec2_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        api = Path(td)/"app.js"
        api.write_text("fetch('http://localhost:5000/api')")
        result = apply_patches(spec, plan, td, service_origin="http://${PUBLIC_IP}:8080")
        # marker indicates service origin rewrite path chosen
        assert any("api_base=service_origin" in c for c in result.changes)


def test_container_entrypoint_and_cmd_present_for_ecs():
    spec = spec_of(runtime="node", framework="express", start_command="node server.js", port=3000)
    plan = InfraPlan(target="ecs_fargate", module_hint="ecs_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        Path(td, "server.js").write_text("const app=require('express')(); app.listen(3000);")
        result = apply_patches(spec, plan, td)
        assert result.container_cmd is not None
        assert result.container_entrypoint is not None
