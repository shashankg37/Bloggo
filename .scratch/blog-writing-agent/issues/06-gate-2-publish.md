# 06: Gate 2 and publish — finish the Run

**What to build:** The Run pauses at Gate 2 for final review, with status showing the pending Gate and the final Draft. Resuming with approve publishes the Markdown post: to the default location (`runs/<thread_id>/final.md`) or to the output path supplied in the Brief; when the Run was force-accepted after the Revision cap, the outstanding Critique is written into the final file's header comment. Resuming with revise plus feedback returns to drafting, then re-pauses at Gate 2. On publish the Run reaches a completed state and the graph ends — the first ticket where a Run runs the full lifecycle: start → Gate 1 → draft loop → Gate 2 → published post.

**Blocked by:** 05: Draft, Critique, and the Revision loop

**Status:** ready-for-agent

- [ ] Status reports the pending Gate 2 with the final Draft payload
- [ ] Approving publishes the post to the default `runs/<thread_id>/final.md` location
- [ ] An output path supplied in the Brief overrides the default location
- [ ] Force-accepted Runs carry the outstanding Critique as a header comment in the published file
- [ ] Revise at Gate 2 redrafts and re-pauses at Gate 2
- [ ] A completed Run reports a terminal status
- [ ] An end-to-end HTTP-seam test walks a Run from Brief to published file
