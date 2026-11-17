# 04: Outline stage and Gate 1 — the first human pause

**What to build:** The pipeline proposes an Outline from the Brief, plan, and Research Notes, saves it as an Artifact, and pauses at Gate 1 via a LangGraph interrupt. `GET /runs/{id}` shows the pending Gate together with the Outline payload it wants approved. `POST /runs/{id}/resume` accepts a Gate Decision: approve proceeds past the Gate; revise with feedback routes back to outline re-drafting, with the feedback stored in state (routing keys off feedback presence — empty feedback means approved). A revised pass produces a fresh Outline Artifact.

**Blocked by:** 03: Researcher stage

**Status:** ready-for-agent

- [ ] The Run pauses at Gate 1 after the Outline is drafted, and the server can be idle at the pause without losing the Run
- [ ] Status reports the pending Gate and includes the Outline payload
- [ ] Resuming with approve moves the Run past Gate 1 toward drafting
- [ ] Resuming with revise plus feedback re-runs the Outline with the feedback reflected in state, and a new Outline Artifact is written
- [ ] An Outline Artifact is written on every outline pass
- [ ] HTTP-seam tests cover pause, approve, and revise flows
