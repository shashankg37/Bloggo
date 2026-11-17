# 05: Draft, Critique, and the Revision loop

**What to build:** The post gets drafted from the approved Outline and Research Notes; the Critic evaluates each Draft and returns structured output — critique text plus a Verdict (`revise` | `approve`). A conditional edge runs the revise loop: while the Verdict is `revise` and the Revision count is below 2, the draft node redrafts, incrementing the Revision count only when redrafting from feedback; past the cap the loop force-accepts the last Draft, keeping the outstanding Critique available for the publish header. Each Draft version lands as a numbered Artifact.

**Blocked by:** 04: Outline stage and Gate 1

**Status:** ready-for-agent

- [ ] A Draft Artifact is written per version, numbered
- [ ] Each Critique is recorded in state with its Verdict
- [ ] A `revise` Verdict below the Revision cap routes back to redrafting exactly once per revision, with the count incremented only on redrafts
- [ ] The loop exits deterministically once the Revision cap is reached, force-accepting the last Draft
- [ ] The outstanding Critique survives in state for the publish stage when force-accepted
- [ ] The fake chat model's script controls Verdicts so loop scenarios (approve first time, revise then approve, always-revise to the cap) are deterministic
- [ ] HTTP-seam tests observe the loop externally — via status transitions and Artifacts — never via internals
