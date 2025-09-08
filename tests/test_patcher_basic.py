import tempfile
from pathlib import Path
from arvo.patcher import apply_patches
from arvo.analyzer.spec import DeploymentSpec
from arvo.selector.plan import InfraPlan


def make_spec(runtime="python", framework="flask", port=5000):
    return DeploymentSpec(
        app_path="/app",
        runtime=runtime,
        framework=framework,
        containerized=False,
        multi_service=False,
        start_command="flask run",
        port=port,
        health_path="/health",
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


def test_flask_localhost_rewrite_and_systemd():
    spec = make_spec()
    plan = InfraPlan(target="ec2", module_hint="ec2_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p/"app.py").write_text("from flask import Flask\napp=Flask(__name__)\n# http://localhost:5000/api\napp.run(host='127.0.0.1', port=5000)\n")
        result = apply_patches(spec, plan, td)
        assert result.systemd_unit is not None
        assert result.env_overrides["PORT"] == str(spec.port)
        # idempotent second run
        result2 = apply_patches(spec, plan, td)
        assert len(result2.changes) >= 0


def test_express_listen_rewrite_and_container_cmd():
    spec = make_spec(runtime="node", framework="express", port=3000)
    plan = InfraPlan(target="ecs_fargate", module_hint="ecs_web", parameters={})
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p/"server.js").write_text("const app=require('express')(); app.listen(3000,'127.0.0.1');")
        result = apply_patches(spec, plan, td)
        assert result.container_cmd is not None
        assert result.env_overrides["PORT"] == str(spec.port)
