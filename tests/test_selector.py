from arvo.selector import select_infra
from arvo.analyzer.spec import DeploymentSpec


def make_spec(**kw):
    base = dict(
        app_path="/tmp/app",
        runtime="python",
        framework="flask",
        containerized=False,
        multi_service=False,
        start_command="flask run",
        port=5000,
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
    base.update(kw)
    return DeploymentSpec(**base)


def test_flask_defaults_to_ec2():
    spec = make_spec(runtime="python", framework="flask", containerized=False)
    plan = select_infra(spec)
    assert plan.target == "ec2"
    assert plan.module_hint == "ec2_web"
    assert any("framework=flask" in r for r in plan.rationale)


def test_django_defaults_to_ec2():
    spec = make_spec(runtime="python", framework="django")
    plan = select_infra(spec)
    assert plan.target == "ec2"


def test_containerized_chooses_ecs():
    spec = make_spec(containerized=True)
    plan = select_infra(spec)
    assert plan.target in {"ecs_fargate", "lightsail_containers"}


def test_dockerfile_chooses_ecs():
    spec = make_spec(manifests={"Dockerfile": "/tmp/app/Dockerfile"})
    plan = select_infra(spec)
    assert plan.target in {"ecs_fargate", "lightsail_containers"}


def test_static_site_s3_cf():
    spec = make_spec(runtime="static", framework=None, static_assets="build/", start_command=None, port=None)
    plan = select_infra(spec)
    assert plan.target == "s3_cf"
    assert plan.module_hint == "static_site"


def test_overrides_win():
    spec = make_spec()
    plan = select_infra(spec, overrides={"infra": "ecs_fargate", "region": "us-west-2"})
    assert plan.target == "ecs_fargate"
    assert plan.parameters.get("region") == "us-west-2"


def test_lambda_stub_falls_back():
    spec = make_spec()
    plan = select_infra(spec, overrides={"infra": "lambda"})
    assert plan.target == "ec2" or plan.fallback_used
