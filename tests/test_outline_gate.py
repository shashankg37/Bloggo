"""Gate 1 over the HTTP seam: the Run pauses for the Outline decision.

The fake chat model scripts the whole pipeline — plan, research notes,
outline — and the search tool is stubbed offline. Decisions flow through
`POST /runs/{id}/resume`; the Run's state machine is observed by polling.
"""

from langchain_core.messages import AIMessage

from tests.helpers import start_run, wait_for_gate, wait_for_status


def script_to_outline(model, outline: str) -> None:
    """Script plan → research → outline responses for one outline pass."""
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


def test_run_pauses_at_gate_1_with_outline_payload(
    client, fake_chat_model, offline_search
) -> None:
    script_to_outline(fake_chat_model, "# Outline\n- Intro: why state\n- Body")
    run_id = start_run(client)

    gate = wait_for_gate(client, run_id)

    assert gate == {"gate": "outline", "outline": "# Outline\n- Intro: why state\n- Body"}
    fetched = client.get(f"/runs/{run_id}/artifacts/outline.md")
    assert fetched.status_code == 200
    assert "why state" in fetched.text


def test_approving_gate_1_completes_the_run(
    client, fake_chat_model, offline_search
) -> None:
    script_to_outline(fake_chat_model, "# Outline\n- Intro only")
    run_id = start_run(client)
    wait_for_gate(client, run_id)

    response = client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

    assert response.status_code == 202
    wait_for_status(client, run_id, "completed")


def test_revising_reruns_outline_with_feedback_and_repause(
    client, fake_chat_model, offline_search
) -> None:
    script_to_outline(fake_chat_model, "# Outline v1\n- Intro only")
    run_id = start_run(client)
    wait_for_gate(client, run_id)

    # The revised pass consumes a fresh scripted response (the 4th model call).
    fake_chat_model.responses = fake_chat_model.responses + [
        AIMessage(content="# Outline v2\n- persistence section")
    ]

    response = client.post(
        f"/runs/{run_id}/resume",
        json={"decision": "revise", "feedback": "Add a section on persistence"},
    )
    assert response.status_code == 202

    gate = wait_for_gate(client, run_id, contains="persistence")

    assert gate["gate"] == "outline"
    assert "persistence" in gate["outline"]
    fetched = client.get(f"/runs/{run_id}/artifacts/outline.md")
    assert "persistence" in fetched.text

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})
    wait_for_status(client, run_id, "completed")


def test_revise_without_feedback_is_a_validation_error(
    client, fake_chat_model, offline_search
) -> None:
    script_to_outline(fake_chat_model, "# Outline\n- Intro only")
    run_id = start_run(client)
    wait_for_gate(client, run_id)

    response = client.post(f"/runs/{run_id}/resume", json={"decision": "revise"})

    assert response.status_code == 422


def test_unknown_decision_is_a_validation_error(
    client, fake_chat_model, offline_search
) -> None:
    script_to_outline(fake_chat_model, "# Outline\n- Intro only")
    run_id = start_run(client)
    wait_for_gate(client, run_id)

    response = client.post(f"/runs/{run_id}/resume", json={"decision": "maybe"})

    assert response.status_code == 422


def test_resuming_a_run_not_awaiting_a_gate_is_a_conflict(
    client, fake_chat_model, offline_search
) -> None:
    script_to_outline(fake_chat_model, "# Outline\n- Intro only")
    run_id = start_run(client)
    wait_for_gate(client, run_id)
    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})
    wait_for_status(client, run_id, "completed")

    response = client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

    assert response.status_code == 409
    assert "not awaiting" in response.json()["detail"]


def test_resuming_unknown_run_is_a_404(client) -> None:
    response = client.post("/runs/nope/resume", json={"decision": "approve"})

    assert response.status_code == 404
    assert "Unknown Run" in response.json()["detail"]
