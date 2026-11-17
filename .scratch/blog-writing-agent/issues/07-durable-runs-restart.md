# 07: Durable Runs — resume across a server restart

**What to build:** Proof that persistence is real, not incidental: a Run that reaches a Gate, has its server stopped and restarted, and is then resumed by its Run identifier continues from its Checkpoint — Research Notes, approved Outline, Drafts, and Revision count all intact — and completes. Any fixes this exposes to checkpointer configuration are in scope; no new features.

**Blocked by:** 04: Outline stage and Gate 1

**Status:** done

- [x] A Run paused at a Gate resumes after a full server restart, continuing from its Checkpoint rather than restarting the pipeline
- [x] State accumulated before the restart (Research Notes, Outline, Revision count) is intact after it
- [x] The test simulates the restart between HTTP calls using a temporary SQLite checkpointer file
- [x] A resumed Run completes through the remaining pipeline stages

**Notes:** No fixes needed — the `ThreadSafeSqliteSaver` over one shared connection, and status derived from `graph.get_state`, already made persistence real. The tests build two app instances against the same SQLite file and runs folder; the first fully shuts down (executor drained, connection closed) before the second starts, so nothing in memory carries over. Two proofs: a paused Run resumes and completes with pre-restart Research Notes intact, and an Outline revision made *before* the restart still drives the post-restart draft. Script misalignment would fail these tests deterministically — a pipeline restart from scratch would consume the wrong scripted responses.
