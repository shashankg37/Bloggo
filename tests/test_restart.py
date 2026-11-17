"""Durable Runs: a paused Run survives a full server restart.

Two app instances are built against the *same* SQLite checkpoint file and
runs folder; the first one fully shuts down (executor drained, connection
closed) before the second starts. Nothing in memory carries over — whatever
the resumed Run knows, it knows from its Checkpoint on disk.
"""

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from blog_agent import config
from blog_agent.api import create_app
from tests.helpers import (
    artifacts,
    script_draft_and_approve,
    script_pipeline,
    start_run,
    wait_for_gate,
    wait_for_status,
)


def test_paused_run_resumes_after_full_server_restart(
    tmp_path, fake_chat_model, offline_search
) -> None:
    settings = config.Settings(
        checkpoint_db=str(tmp_path / "checkpoints.sqlite"),
        runs_dir=str(tmp_path / "runs"),
    )
    script_pipeline(fake_chat_model, "# Outline\n- Intro\n- Body")

    with TestClient(create_app(settings=settings)) as first:
        run_id = start_run(first)
        gate = wait_for_gate(first, run_id)
    # The server is fully down here: no executor, no open connection.

    with TestClient(create_app(settings=settings)) as second:
        status = second.get(f"/runs/{run_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "awaiting_gate"
        assert status.json()["gate"] == gate  # the same pending Outline

        # Research Notes survived: the Artifact written before the restart.
        notes = second.get(f"/runs/{run_id}/artifacts/research.md")
        assert "durable state matters" in notes.text

        script_draft_and_approve(fake_chat_model, draft="# Draft\n\nWritten post-restart.")
        response = second.post(f"/runs/{run_id}/resume", json={"decision": "approve"})
        assert response.status_code == 202

        wait_for_status(second, run_id, "completed")
        assert artifacts(second, run_id) == [
            "draft_v1.md",
            "outline.md",
            "research.md",
        ]
        draft = second.get(f"/runs/{run_id}/artifacts/draft_v1.md")
        assert "Written post-restart." in draft.text


def test_state_from_before_the_restart_drives_the_continued_pipeline(
    tmp_path, fake_chat_model, offline_search
) -> None:
    """A revision made before the restart still shapes the post-restart draft."""
    settings = config.Settings(
        checkpoint_db=str(tmp_path / "checkpoints.sqlite"),
        runs_dir=str(tmp_path / "runs"),
    )
    script_pipeline(fake_chat_model, "# Outline v1\n- Intro only")

    with TestClient(create_app(settings=settings)) as first:
        run_id = start_run(first)
        wait_for_gate(first, run_id)
        # The revised outline pass consumes a fresh scripted response.
        fake_chat_model.responses = fake_chat_model.responses + [
            AIMessage(content="# Outline v2\n- persistence section")
        ]
        revised = first.post(
            f"/runs/{run_id}/resume",
            json={"decision": "revise", "feedback": "Add persistence"},
        )
        assert revised.status_code == 202
        gate = wait_for_gate(first, run_id, contains="persistence")
    # Restart between the revision and its approval.

    with TestClient(create_app(settings=settings)) as second:
        status = second.get(f"/runs/{run_id}")
        assert status.json()["status"] == "awaiting_gate"
        assert status.json()["gate"] == gate  # revised Outline, feedback intact

        script_draft_and_approve(
            fake_chat_model, draft="# Draft\n\nBuilt on the revised outline."
        )
        second.post(f"/runs/{run_id}/resume", json={"decision": "approve"})

        wait_for_status(second, run_id, "completed")
        draft = second.get(f"/runs/{run_id}/artifacts/draft_v1.md")
        assert "Built on the revised outline." in draft.text
