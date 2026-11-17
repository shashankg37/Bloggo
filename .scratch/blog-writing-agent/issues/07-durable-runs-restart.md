# 07: Durable Runs — resume across a server restart

**What to build:** Proof that persistence is real, not incidental: a Run that reaches a Gate, has its server stopped and restarted, and is then resumed by its Run identifier continues from its Checkpoint — Research Notes, approved Outline, Drafts, and Revision count all intact — and completes. Any fixes this exposes to checkpointer configuration are in scope; no new features.

**Blocked by:** 04: Outline stage and Gate 1

**Status:** ready-for-agent

- [ ] A Run paused at a Gate resumes after a full server restart, continuing from its Checkpoint rather than restarting the pipeline
- [ ] State accumulated before the restart (Research Notes, Outline, Revision count) is intact after it
- [ ] The test simulates the restart between HTTP calls using a temporary SQLite checkpointer file
- [ ] A resumed Run completes through the remaining pipeline stages
