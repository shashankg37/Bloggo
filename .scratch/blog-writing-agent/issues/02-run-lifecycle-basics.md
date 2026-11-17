# 02: Run lifecycle basics — start a Run, poll a Run

**What to build:** The Run lifecycle over the API: `POST /runs` accepts a Brief (topic, audience, tone, target word count, optional output path) and returns a Run identifier; the Run is backed by a SQLite checkpointer thread and its Artifact folder is created on disk; `GET /runs/{id}` reports Run status; unknown Run identifiers return a structured error. A minimal pipeline skeleton (a single pass-through stage) executes through the graph and checkpointer so the graph → Checkpoint → API wiring is proven end-to-end — a complete, if trivial, vertical slice.

**Blocked by:** 01: Scaffold, config, and server skeleton

**Status:** ready-for-agent

- [ ] `POST /runs` with a Brief returns a Run identifier and the Run persists across requests
- [ ] `GET /runs/{id}` reports the Run's status
- [ ] Unknown Run identifiers return a structured, client-friendly error
- [ ] The Run's Artifact folder is created on disk under the shared runs location
- [ ] The minimal pipeline executes through the SQLite checkpointer, with state persisted in the checkpoint
- [ ] HTTP-seam tests cover start, poll, and error cases using the fake chat model
