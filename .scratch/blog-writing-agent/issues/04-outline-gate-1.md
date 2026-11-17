# 04: Outline stage and Gate 1 — the first human pause

**What to build:** The pipeline proposes an Outline from the Brief, plan, and Research Notes, saves it as an Artifact, and pauses at Gate 1 via a LangGraph interrupt. `GET /runs/{id}` shows the pending Gate together with the Outline payload it wants approved. `POST /runs/{id}/resume` accepts a Gate Decision: approve proceeds past the Gate; revise with feedback routes back to outline re-drafting, with the feedback stored in state (routing keys off feedback presence — empty feedback means approved). A revised pass produces a fresh Outline Artifact.

**Blocked by:** 03: Researcher stage

**Status:** done

- [x] The Run pauses at Gate 1 after the Outline is drafted, and the server can be idle at the pause without losing the Run
- [x] Status reports the pending Gate and includes the Outline payload
- [x] Resuming with approve moves the Run past Gate 1 toward drafting (currently to END; ticket 05 rewires the edge to the draft stage)
- [x] Resuming with revise plus feedback re-runs the Outline with the feedback reflected in state, and a new Outline Artifact is written
- [x] An Outline Artifact is written on every outline pass (overwrites `outline.md`; drafts get versioned filenames in ticket 05, the Outline stays a single file per spec)
- [x] HTTP-seam tests cover pause, approve, and revise flows

**Notes:** The Gate is a LangGraph `interrupt` inside the `outline_gate` node; `POST /runs/{id}/resume` submits `Command(resume=payload)` on the executor. Verified empirically on LangGraph 1.2: `graph.invoke` *returns* at an interrupt (result carries `__interrupt__`), it does not raise, so the executor's `except Exception` error path is safe. Routing keys off `outline_feedback` presence (empty = approved); malformed decisions (unknown `decision`, revise without feedback) are 422 via a Pydantic `Literal` + `model_validator`; resume on a Run not awaiting a Gate is 409; unknown Run is 404. `wait_for_gate(contains=...)` polls until a *fresh* outline appears, avoiding stale-gate races in tests.
