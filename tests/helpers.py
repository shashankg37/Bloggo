"""Helpers for HTTP-seam tests: start Runs and poll them to a status."""

import time

from fastapi.testclient import TestClient


def start_run(client: TestClient, topic: str = "Agentic state with LangGraph", **brief) -> str:
    response = client.post("/runs", json={"topic": topic, **brief})
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def wait_for_status(
    client: TestClient,
    run_id: str,
    status: str,
    timeout: float = 10.0,
):
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
