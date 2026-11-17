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


def wait_for_gate(
    client: TestClient,
    run_id: str,
    contains: str | None = None,
    timeout: float = 10.0,
) -> dict:
    """Poll until the Run is paused at a Gate.

    With `contains`, keeps polling until the Gate's outline payload mentions
    the marker — so a revision's *fresh* outline is waited for, not the stale
    one from the previous pass.
    """
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = client.get(f"/runs/{run_id}")
        assert last.status_code == 200, last.text
        body = last.json()
        if body["status"] == "awaiting_gate" and (
            contains is None or contains in body["gate"].get("outline", "")
        ):
            return body["gate"]
        time.sleep(0.05)
    raise AssertionError(f"Run never paused at a matching Gate; last: {last.text}")
