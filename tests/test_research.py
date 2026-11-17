"""Researcher stage over the HTTP seam: plan + tool-calling research.

The fake chat model scripts the whole interaction — a plan, then a search
tool call, then the final notes — and the search tool is stubbed offline.
Everything is verified through status transitions and Artifacts.
"""

from langchain_core.messages import AIMessage

from tests.helpers import start_run, wait_for_status


def script_research(model, plan: str, notes: str, query: str = "agentic state") -> None:
    model.responses = [
        AIMessage(content=plan),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "web_search", "args": {"query": query}, "id": "call_1"}
            ],
        ),
        AIMessage(content=notes),
    ]


def test_plan_and_research_produce_notes_and_artifact(client, fake_chat_model, offline_search) -> None:
    script_research(
        fake_chat_model,
        plan="Angle: state as the spine of the agent.",
        notes="## Research Notes\n- LangGraph state flows through nodes",
    )
    run_id = start_run(client)
    wait_for_status(client, run_id, "awaiting_gate")

    listing = client.get(f"/runs/{run_id}/artifacts")
    assert listing.status_code == 200
    assert [a["name"] for a in listing.json()["artifacts"]] == [
        "outline.md",
        "research.md",
    ]

    fetched = client.get(f"/runs/{run_id}/artifacts/research.md")
    assert fetched.status_code == 200
    assert "LangGraph state flows through nodes" in fetched.text
    assert fetched.headers["content-type"].startswith("text/markdown")

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})
    wait_for_status(client, run_id, "completed")


def test_researcher_can_finish_without_searching(client, fake_chat_model, offline_search) -> None:
    fake_chat_model.responses = [
        AIMessage(content="Angle: interrupts and checkpoints."),
        AIMessage(content="## Research Notes\n- Model knowledge suffices here"),
    ]
    run_id = start_run(client)
    wait_for_status(client, run_id, "awaiting_gate")

    fetched = client.get(f"/runs/{run_id}/artifacts/research.md")
    assert "Model knowledge suffices here" in fetched.text

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})
    wait_for_status(client, run_id, "completed")


def test_stage_failure_becomes_run_error_status(client, fake_chat_model, offline_search) -> None:
    fake_chat_model.responses = [
        AIMessage(content="Angle: durable Runs."),
        RuntimeError("scripted model failure"),
    ]
    run_id = start_run(client)

    final = wait_for_status(client, run_id, "error")

    assert "scripted model failure" in final["error"]


def test_artifacts_404_for_unknown_run(client) -> None:
    response = client.get("/runs/nope/artifacts")

    assert response.status_code == 404
    assert "Unknown Run" in response.json()["detail"]


def test_artifact_traversal_is_blocked(client, fake_chat_model, offline_search) -> None:
    script_research(fake_chat_model, plan="p", notes="n")
    run_id = start_run(client)
    wait_for_status(client, run_id, "awaiting_gate")

    response = client.get(f"/runs/{run_id}/artifacts/..%2F..%2F.env")

    assert response.status_code == 404
