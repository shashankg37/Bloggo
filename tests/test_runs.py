"""Run lifecycle basics over the HTTP seam: start a Run, poll a Run.

Tests act as API clients only — they never touch the graph, the checkpointer,
or node functions. Status transitions are observed by polling.
"""

import time

import pytest
from fastapi.testclient import TestClient

from blog_agent import config
from blog_agent.api import create_app


@pytest.fixture
def client(tmp_path):
    settings = config.Settings(
        checkpoint_db=str(tmp_path / "checkpoints.sqlite"),
        runs_dir=str(tmp_path / "runs"),
    )
    with TestClient(create_app(settings=settings)) as test_client:
        yield test_client


def wait_for_status(client: TestClient, run_id: str, status: str, timeout: float = 10.0):
    """Poll a Run until it reaches the wanted status (or fail loudly)."""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = client.get(f"/runs/{run_id}")
        assert last.status_code == 200, last.text
        if last.json()["status"] == status:
            return last.json()
        time.sleep(0.05)
    raise AssertionError(f"Run never reached {status!r}; last: {last.text}")


def start_run(client: TestClient, topic: str = "Agentic state with LangGraph") -> str:
    response = client.post("/runs", json={"topic": topic})
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def test_start_run_returns_a_run_identifier(client) -> None:
    response = client.post("/runs", json={"topic": "Agentic state with LangGraph"})

    assert response.status_code == 202
    body = response.json()
    assert body["run_id"]
    assert body["status"] == "running"


def test_run_executes_and_reaches_completed(client, tmp_path) -> None:
    run_id = start_run(client)

    final = wait_for_status(client, run_id, "completed")

    assert final["run_id"] == run_id


def test_run_artifact_folder_is_created_on_disk(client, tmp_path) -> None:
    run_id = start_run(client)
    wait_for_status(client, run_id, "completed")

    assert (tmp_path / "runs" / run_id).is_dir()


def test_unknown_run_returns_structured_404(client) -> None:
    response = client.get("/runs/deadbeef00")

    assert response.status_code == 404
    assert "Unknown Run" in response.json()["detail"]


def test_malformed_brief_returns_validation_error(client) -> None:
    response = client.post("/runs", json={})

    assert response.status_code == 422


def test_target_words_must_be_positive(client) -> None:
    response = client.post("/runs", json={"topic": "x", "target_words": 0})

    assert response.status_code == 422


def test_brief_defaults_fill_in(client) -> None:
    """A minimal Brief is accepted; the server fills in sensible defaults."""
    response = client.post("/runs", json={"topic": "Agentic state"})

    assert response.status_code == 202
