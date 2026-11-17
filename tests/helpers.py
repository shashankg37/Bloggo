"""Helpers for HTTP-seam tests: start Runs and poll them to a status."""

import time

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


def start_run(client: TestClient, topic: str = "Agentic state with LangGraph", **brief) -> str:
    response = client.post("/runs", json={"topic": topic, **brief})
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def script_draft_and_approve(
    model, draft: str = "# Draft\n\nThe post body.", critique: str = "Ready to publish."
) -> None:
    """Extend the script so the Run completes after Gate 1 approval.

    Appends one draft response and one approving Critique (structured-output
    JSON). Call it before posting the approve decision.
    """
    model.responses = model.responses + [
        AIMessage(content=draft),
        AIMessage(content=f'{{"critique": "{critique}", "verdict": "approve"}}'),
    ]


def script_pipeline(model, outline: str) -> None:
    """Script plan → research → outline for one Run."""
    model.responses = [
        AIMessage(content="Angle: state as the spine of the agent."),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "web_search",
                    "args": {"query": "langgraph state"},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="## Research Notes\n- durable state matters"),
        AIMessage(content=outline),
    ]


def script_verdict(model, critique: str, verdict: str) -> None:
    """Append one Draft response plus one Critic Verdict to the script."""
    model.responses = model.responses + [
        AIMessage(content=f"# Draft\n\nBody for: {critique}"),
        AIMessage(content=f'{{"critique": "{critique}", "verdict": "{verdict}"}}'),
    ]


def artifacts(client: TestClient, run_id: str) -> list[str]:
    """The Run's Artifact names, in list order."""
    listing = client.get(f"/runs/{run_id}/artifacts")
    assert listing.status_code == 200
    return [a["name"] for a in listing.json()["artifacts"]]


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
