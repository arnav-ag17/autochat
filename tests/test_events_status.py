from arvo.events import emit_event, get_status_from_events
from arvo.state import create_deployment_dir
from arvo.ids import new_deployment_id

def test_status_progression_basic(tmp_path):
    deployment_id = new_deployment_id()
    # use tmp dir as ARVO_HOME
    import os
    os.environ['ARVO_HOME'] = str(tmp_path)
    create_deployment_dir(deployment_id)
    emit_event(deployment_id, "INIT", {})
    assert get_status_from_events(deployment_id) == "queued"
    emit_event(deployment_id, "TF_INIT", {})
    assert get_status_from_events(deployment_id) == "init"
    emit_event(deployment_id, "DONE", {})
    assert get_status_from_events(deployment_id) == "healthy"
