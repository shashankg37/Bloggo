"""FastAPI application: the Run lifecycle over REST (polling).

- `POST /runs` accepts a Brief and starts a Run in the background, returning
  its Run identifier (a LangGraph checkpointer thread ID).
- `GET /runs/{id}` reports Run status, derived from the Checkpoint so it
  survives server restarts: running (with the active pipeline stage),
  awaiting a Gate (ticket 04), completed, or error.
- Unknown Run identifiers return a structured 404.

Status is never guessed: it is read from the persisted Checkpoint, which is
what makes resume-after-restart (ticket 07) work without extra bookkeeping.
"""

from __future__ import annotations

import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from blog_agent import config, graph as graph_module
from blog_agent.persistence import ThreadSafeSqliteSaver
from blog_agent.state import BlogState


class BriefRequest(BaseModel):
    """The input to a Run."""

    topic: str = Field(min_length=1)
    audience: str = "general readers"
    tone: str = "conversational"
    target_words: int = Field(default=800, gt=0)
    output_path: str | None = None


class RunStatus(BaseModel):
    """Machine-readable Run status: distinguish pipeline progress from Gates."""

    run_id: str
    status: str  # "running" | "awaiting_gate" | "completed" | "error"
    active_node: str | None = None
    error: str | None = None


def create_app(settings: config.Settings | None = None) -> FastAPI:
    """Build the FastAPI app against the given (or default) settings.

    Tests pass temporary checkpoint and runs paths here; the server entrypoint
    uses the settings module's defaults read from `.env`.
    """
    settings = settings or config.get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # The checkpointer and the runs folder are created on first use.
        Path(settings.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
        Path(settings.runs_dir).mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            settings.checkpoint_db, check_same_thread=False
        )
        saver = ThreadSafeSqliteSaver(connection)
        app.state.settings = settings
        app.state.saver = saver
        app.state.graph = graph_module.build_graph(saver)
        app.state.executor = ThreadPoolExecutor(max_workers=4)
        app.state.known_runs: set[str] = set()
        try:
            yield
        finally:
            # Wait for in-flight pipeline tasks: they keep writing to the
            # shared connection, which must not close underneath them.
            app.state.executor.shutdown(wait=True)
            connection.close()

    app = FastAPI(
        title="Blog Writing Agent",
        description="Topic in, Markdown post out, with human Gates and durable Runs.",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe: the server is up."""
        return {"status": "ok"}

    @app.post("/runs", status_code=202)
    def start_run(brief: BriefRequest) -> dict:
        run_id = uuid.uuid4().hex
        Path(settings.runs_dir, run_id).mkdir(parents=True, exist_ok=True)
        initial: BlogState = {
            "topic": brief.topic,
            "audience": brief.audience,
            "tone": brief.tone,
            "target_words": brief.target_words,
            "output_path": brief.output_path or "",
            "research_notes": [],
            "revision_count": 0,
            "error": "",
        }
        run_config = {
            "configurable": {
                "thread_id": run_id,
                "runs_dir": str(settings.runs_dir),
            }
        }
        graph = app.state.graph
        app.state.known_runs.add(run_id)

        def execute() -> None:
            try:
                graph.invoke(initial, run_config)
            except Exception as exc:  # noqa: BLE001 — surface any stage failure as Run state
                graph.update_state(
                    run_config, {"error": f"{type(exc).__name__}: {exc}"}
                )

        app.state.executor.submit(execute)
        return {"run_id": run_id, "status": "running"}

    @app.get("/runs/{run_id}")
    def run_status(run_id: str) -> RunStatus:
        snapshot = app.state.graph.get_state(
            {"configurable": {"thread_id": run_id}}
        )
        if not snapshot.values:
            # No checkpoint exists. A Run started in this process may simply
            # not have written its first checkpoint yet.
            if run_id not in app.state.known_runs:
                raise HTTPException(status_code=404, detail=f"Unknown Run: {run_id}")
            return RunStatus(run_id=run_id, status="running")

        values = snapshot.values
        if values.get("error"):
            return RunStatus(
                run_id=run_id, status="error", error=values["error"]
            )
        interrupts = [i for task in snapshot.tasks for i in task.interrupts]
        if interrupts:
            # Gate payload exposure arrives with the Gate stages (ticket 04).
            return RunStatus(run_id=run_id, status="awaiting_gate")
        if not snapshot.next:
            return RunStatus(run_id=run_id, status="completed")
        return RunStatus(
            run_id=run_id, status="running", active_node=snapshot.next[0]
        )

    @app.get("/runs/{run_id}/artifacts")
    def list_artifacts(run_id: str) -> dict:
        folder = Path(settings.runs_dir, run_id)
        if not folder.is_dir():
            raise HTTPException(status_code=404, detail=f"Unknown Run: {run_id}")
        artifacts = [
            {"name": artifact.name, "size": artifact.stat().st_size}
            for artifact in sorted(folder.iterdir())
            if artifact.is_file()
        ]
        return {"run_id": run_id, "artifacts": artifacts}

    @app.get("/runs/{run_id}/artifacts/{filename}")
    def fetch_artifact(run_id: str, filename: str) -> Response:
        folder = (Path(settings.runs_dir) / run_id).resolve()
        target = (folder / filename).resolve()
        if not target.is_relative_to(folder) or not target.is_file():
            raise HTTPException(status_code=404, detail=f"Unknown Artifact: {filename}")
        return Response(
            content=target.read_text(encoding="utf-8"), media_type="text/markdown"
        )

    return app


app = create_app()
