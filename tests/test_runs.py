"""Run lifecycle basics over the HTTP seam: start a Run, poll a Run.

Tests act as API clients only — they never touch the graph, the checkpointer,
or node functions. Status transitions are observed by polling.
"""

from langchain_core.messages import AIMessage

from tests.helpers import script_draft_and_approve, start_run, wait_for_gate, wait_for_status


def test_start_run_returns_a_run_identifier(client, fake_chat_model, offline_search) -> None:
    response = client.post("/runs", json={"topic": "Agentic state with LangGraph"})

    assert response.status_code == 202
    body = response.json()
    assert body["run_id"]
    assert body["status"] == "running"


def test_run_executes_and_reaches_completed(client, fake_chat_model, offline_search) -> None:
    run_id = start_run(client)
    gate = wait_for_gate(client, run_id)  # the pipeline pauses at Gate 1 (ticket 04)
    assert gate["outline"]
    script_draft_and_approve(fake_chat_model)

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

    final = wait_for_status(client, run_id, "completed")
    assert final["run_id"] == run_id


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


def test_brief_defaults_fill_in(client, fake_chat_model, offline_search) -> None:
    """A minimal Brief is accepted; the server fills in sensible defaults."""
    response = client.post("/runs", json={"topic": "Agentic state"})

    assert response.status_code == 202
