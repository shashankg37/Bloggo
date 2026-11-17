# 02: Run lifecycle basics — start a Run, poll a Run

**What to build:** The Run lifecycle over the API: `POST /runs` accepts a Brief (topic, audience, tone, target word count, optional output path) and returns a Run identifier; the Run is backed by a SQLite checkpointer thread and its Artifact folder is created on disk; `GET /runs/{id}` reports Run status; unknown Run identifiers return a structured error. A minimal pipeline skeleton (a single pass-through stage) executes through the graph and checkpointer so the graph → Checkpoint → API wiring is proven end-to-end — a complete, if trivial, vertical slice.

**Blocked by:** 01: Scaffold, config, and server skeleton

**Status:** done

- [x] `POST /runs` with a Brief returns a Run identifier and the Run persists across requests
- [x] `GET /runs/{id}` reports the Run's status
- [x] Unknown Run identifiers return a structured, client-friendly error
- [x] The Run's Artifact folder is created on disk under the shared runs location
- [x] The minimal pipeline executes through the SQLite checkpointer, with state persisted in the checkpoint
- [x] HTTP-seam tests cover start, poll, and error cases using the fake chat model

**Notes:** Run status is derived from the persisted Checkpoint (with an in-process registry only to cover the pre-first-checkpoint window), so restart-resume needs no extra bookkeeping. Two infrastructure pieces arrived with this ticket: a thread-safe wrapper around the SQLite checkpointer (LangGraph's saver is single-threaded; the API polls while workers execute) and an `error` field on the Run state for stage failures — a small addition to the spec'd schema. Server invocations must use the `uv run python -m uvicorn ...` form.
