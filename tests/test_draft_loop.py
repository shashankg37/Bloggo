"""The Draft → Critique → Revision loop over the HTTP seam.

Verdicts are scripted through the fake chat model (the Critic's structured
output is a JSON response), so approve-first-time, revise-then-approve, and
always-revise-to-the-cap are all deterministic. Tests observe only status
transitions and Artifacts.
"""

from langchain_core.messages import AIMessage

from tests.helpers import script_draft_and_approve, start_run, wait_for_gate, wait_for_status


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


def artifacts(client, run_id: str) -> list[str]:
    listing = client.get(f"/runs/{run_id}/artifacts")
    assert listing.status_code == 200
    return [a["name"] for a in listing.json()["artifacts"]]


def test_approve_first_time_writes_one_draft(
    client, fake_chat_model, offline_search
) -> None:
    script_pipeline(fake_chat_model, "# Outline\n- Intro\n- Body")
    run_id = start_run(client)
    wait_for_gate(client, run_id)
    script_verdict(fake_chat_model, "No issues.", "approve")

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

    wait_for_status(client, run_id, "completed")
    assert artifacts(client, run_id) == [
        "draft_v1.md",
        "outline.md",
        "research.md",
    ]
    fetched = client.get(f"/runs/{run_id}/artifacts/draft_v1.md")
    assert "Body for: No issues." in fetched.text


def test_revise_then_approve_redrafts_once(
    client, fake_chat_model, offline_search
) -> None:
    script_pipeline(fake_chat_model, "# Outline\n- Intro\n- Body")
    run_id = start_run(client)
    wait_for_gate(client, run_id)
    script_verdict(fake_chat_model, "Tighten the intro.", "revise")
    script_verdict(fake_chat_model, "Good now.", "approve")

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

    wait_for_status(client, run_id, "completed")
    assert artifacts(client, run_id) == [
        "draft_v1.md",
        "draft_v2.md",
        "outline.md",
        "research.md",
    ]
    fetched_v1 = client.get(f"/runs/{run_id}/artifacts/draft_v1.md")
    assert "Body for: Tighten the intro." in fetched_v1.text
    fetched_v2 = client.get(f"/runs/{run_id}/artifacts/draft_v2.md")
    assert "Body for: Good now." in fetched_v2.text


def test_always_revise_stops_at_the_cap_and_force_accepts(
    client, fake_chat_model, offline_search
) -> None:
    script_pipeline(fake_chat_model, "# Outline\n- Intro\n- Body")
    run_id = start_run(client)
    wait_for_gate(client, run_id)
    script_verdict(fake_chat_model, "Still shallow.", "revise")
    script_verdict(fake_chat_model, "Still shallow again.", "revise")
    script_verdict(fake_chat_model, "Never good enough.", "revise")

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

    # The loop exits deterministically at the Revision cap (2 redrafts),
    # force-accepting draft v3 with the Critique outstanding.
    wait_for_status(client, run_id, "completed")
    assert artifacts(client, run_id) == [
        "draft_v1.md",
        "draft_v2.md",
        "draft_v3.md",
        "outline.md",
        "research.md",
    ]


def test_count_increments_only_on_redrafts_not_on_first_draft(
    client, fake_chat_model, offline_search
) -> None:
    """A first-draft-then-approve Run writes draft_v1, never draft_v2."""
    script_pipeline(fake_chat_model, "# Outline\n- Solo section")
    run_id = start_run(client)
    wait_for_gate(client, run_id)
    script_draft_and_approve(fake_chat_model, draft="# Draft\n\nFirst and only.")

    client.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

    wait_for_status(client, run_id, "completed")
    names = artifacts(client, run_id)
    assert "draft_v1.md" in names
    assert "draft_v2.md" not in names
