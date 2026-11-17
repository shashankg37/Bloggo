# 05: Draft, Critique, and the Revision loop

**What to build:** The post gets drafted from the approved Outline and Research Notes; the Critic evaluates each Draft and returns structured output — critique text plus a Verdict (`revise` | `approve`). A conditional edge runs the revise loop: while the Verdict is `revise` and the Revision count is below 2, the draft node redrafts, incrementing the Revision count only when redrafting from feedback; past the cap the loop force-accepts the last Draft, keeping the outstanding Critique available for the publish header. Each Draft version lands as a numbered Artifact.

**Blocked by:** 04: Outline stage and Gate 1

**Status:** done

- [x] A Draft Artifact is written per version, numbered (`draft_v1.md`, `draft_v2.md`, …)
- [x] Each Critique is recorded in state with its Verdict (`critiques` append reducer)
- [x] A `revise` Verdict below the Revision cap routes back to redrafting exactly once per revision, with the count incremented only on redrafts
- [x] The loop exits deterministically once the Revision cap is reached, force-accepting the last Draft (`force_accept` node; cap = 2)
- [x] The outstanding Critique survives in state for the publish stage when force-accepted (`outstanding_critique`; surfaced in the publish header in ticket 06)
- [x] The fake chat model's script controls Verdicts so loop scenarios (approve first time, revise then approve, always-revise to the cap) are deterministic (`with_structured_output` parses scripted JSON into the Critique schema)
- [x] HTTP-seam tests observe the loop externally — via status transitions and Artifacts — never via internals

**Notes:** The Critic uses `model.with_structured_output(Critique)` (Pydantic schema: critique + Literal verdict), so the real Groq model gets function calling while the fake parses scripted JSON. Routing after the Critic: approve → END for now (ticket 06 wires it to publish), revise with `revision_count < 2` → draft, else → `force_accept` which copies the last critique into `outstanding_critique`. The revision count increments only when a pass redrafts from critique feedback, so draft numbering (`revision_count + 1`) matches artifact names. Tests share a `script_draft_and_approve` helper because every approving test now needs the post-gate draft+critic tail scripted.
