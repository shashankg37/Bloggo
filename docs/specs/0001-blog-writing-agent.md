# Spec 0001 — Blog Writing Agent (LangGraph)

## Problem Statement

Writing a blog post by hand means doing research, structuring an outline, drafting, and revising — a slow, manual loop. The author also wants to learn LangGraph's agentic-state machinery (state, conditional edges, interrupts, persistence) on a project that produces something real, not a toy demo.

## Solution

A blog-writing agent served over FastAPI. The author submits a **Brief** (topic, audience, tone, target word count); a **Run** then plans, researches the web with keyless search tools, proposes an **Outline** that the author approves at a **Gate**, drafts the post, has it critiqued and revised (capped at 2 **Revisions**), and pauses at a second Gate for final approval before publishing the Markdown post to disk. Runs persist in a SQLite checkpointer, so a Run can be paused, the server closed, and the Run resumed later from the same thread ID.

## User Stories

1. As a blog author, I want to submit a Brief (topic, audience, tone, target word count) to the server, so that the agent writes a post tailored to my intent.
2. As a blog author, I want to receive a Run identifier when I submit a Brief, so that I can track, interrupt, and resume that Run.
3. As a blog author, I want to poll a Run's status and see which pipeline stage is active, so that I know what the agent is doing without reading logs.
4. As a blog author, I want the Run to pause at a Gate after the Outline is proposed, so that no prose is written before I endorse the structure.
5. As a blog author, I want a pending Gate to tell me exactly what it wants approved (the Outline content), so that I can make an informed decision.
6. As a blog author, I want to approve the Outline at Gate 1, so that drafting proceeds with my endorsement.
7. As a blog author, I want to send revision feedback at Gate 1 instead of approving, so that the agent rewrites the Outline incorporating my corrections.
8. As a blog author, I want a second Gate before publishing, so that I have final editorial control over the post.
9. As a blog author, I want to approve the final draft at Gate 2, so that the post is written to disk as Markdown.
10. As a blog author, I want to send revision feedback at Gate 2, so that the agent redrafts the post per my notes before I re-review.
11. As a blog author, I want the Researcher to gather real web material using keyless search tools, so that posts are grounded in real sources and I configure zero API keys for research.
12. As a blog author, I want the Researcher bounded to roughly three searches per Run, so that a Run can't spiral into endless research.
13. As a blog author, I want the Critic to return a Verdict (revise or approve) together with a written critique, so that revisions are driven by concrete problems rather than blind redrafting.
14. As a blog author, I want the critique→revise loop capped at 2 Revisions, so that every Run is guaranteed to terminate.
15. As a blog author, I want any outstanding critique recorded in the final file's header when the Revision cap forces acceptance, so that I know what weaknesses remained.
16. As a blog author, I want each stage's Artifact (research notes, outline, draft versions) saved under the Run's folder, so that I can inspect how the post evolved.
17. As a blog author, I want the finished post written to a predictable default location (`runs/<thread_id>/final.md`), so that I always know where the output lands.
18. As a blog author, I want to optionally specify an output path in the Brief, so that finished posts land where my publishing workflow expects them.
19. As a blog author, I want to stop the server mid-Run and resume the Run later by its identifier, so that long Runs aren't lost when I close my machine.
20. As a blog author, I want a resumed Run to continue from its Checkpoint rather than restart, so that completed work (research, approved outline, drafts) is preserved.
21. As an API client, I want a machine-readable status response that distinguishes "pipeline active" from "Gate pending", so that I can automate decisions without parsing prose.
22. As an API client, I want the resume endpoint to accept a structured Gate Decision (approve, or revise plus feedback text), so that automation is trivial.
23. As an API client, I want to list and fetch a Run's Artifacts through the API, so that I can pipe outputs into other tools.
24. As an API client, I want clear, structured errors for unknown Run identifiers or malformed Gate Decisions, so that my integration fails gracefully.
25. As a learner, I want the agentic state defined as one typed schema in one module, so that I can study how state flows through the graph.
26. As a learner, I want list-valued state (research notes) to use an explicit append reducer, so that I can learn how reducers work.
27. As a learner, I want the graph topology in one module with visible conditional edges and interrupts, so that I can trace control flow just by reading it.
28. As a learner, I want the Researcher implemented as a real tool-calling agent (a prebuilt subgraph), so that I can study LangGraph's tool-loop pattern.
29. As a learner, I want the Critic to produce structured output (JSON: critique text plus Verdict), so that I can learn LangChain structured-output patterns.
30. As a learner, I want the model provider configured in exactly one place, read from `.env`, so that swapping providers or models is a one-line change.
31. As a learner, I want `MODEL_NAME` to start blank in `.env`, so that choosing the model is a deliberate decision after the build is complete.
32. As a learner, I want LangSmith tracing dormant and opt-in via environment variables only, so that observability requires no code changes.
33. As a learner, I want tests that drive the full Run lifecycle through the HTTP API with a scripted fake chat model, so that I can see external behavior verified without any API key.
34. As an operator, I want `.env`, the checkpoint database, and run output folders excluded from version control, so that secrets and generated content never leak into git.

## Implementation Decisions

- **Single package, one concern per module**: a state module (the typed agentic state plus reducers), a tools module (keyless search tools), a nodes module (plan / researcher / outline / draft / critic / gates / publish), a graph module (topology, conditional edges, interrupts), a config module (reads `.env`, creates the chat model), an api module (FastAPI app), and an entrypoint module (uvicorn launcher).
- **State schema** (one `TypedDict`; field list settled in design discussion): Brief fields (`topic`, `audience`, `tone`, `target_words`); `research_notes` as a list with an append reducer; `plan`, `outline`, `outline_feedback`; `draft`, `critique`, `revision_feedback`, `revision_count`; `verdict` as a `"revise" | "approve"` enum; `final_markdown`, `output_path`. No chat-message list — this is a task pipeline, not a chatbot.
- **Topology is a fixed pipeline with conditional edges**: plan → researcher → outline → Gate 1 (outline approval) → draft → critique → conditional on Verdict and Revision cap → Gate 2 (final review) → publish → END.
- **Gates use LangGraph `interrupt`.** The human's Gate Decision is written back into state via resume; routing after a Gate keys off the feedback fields (empty feedback = approved; non-empty feedback = revise, routing back to outline or draft). No separate routing field is added.
- **Researcher** is a real tool-calling agent: a prebuilt react-agent subgraph whose model is bound to keyless search tools from the LangChain community ecosystem (DuckDuckGo via the `ddgs` package). No tool-registry abstraction layer; the cap (~3 searches) is enforced by prompt instruction and graph recursion limits.
- **Critic** uses structured output (a PyBinding schema for critique text plus Verdict enum).
- **Revision accounting**: the draft node increments `revision_count` only when redrafting from feedback. The conditional edge after the Critic routes back to draft while Verdict is `revise` and `revision_count < 2`; otherwise it force-accepts, and the publish node writes the outstanding critique into the final file's header comment.
- **Persistence**: a SQLite checkpointer (in the `data/` folder); the checkpointer's `thread_id` identifies a Run, and resuming works across server restarts.
- **API contract** (task-oriented REST, polling — no SSE/websockets): `POST /runs` accepts a Brief plus optional output path and returns the Run identifier; `GET /runs/{id}` returns status — active node, or the pending Gate and the payload it wants approved; `POST /runs/{id}/resume` accepts a Gate Decision (approve, or revise with feedback text); `GET /runs/{id}/artifacts` lists and serves Artifacts. Unknown Run IDs and malformed Gate Decisions return structured errors.
- **Artifacts**: each stage writes its Artifact to `runs/<thread_id>/` as it completes (research notes, outline, numbered drafts); publish writes the final post to `runs/<thread_id>/final.md` unless the Brief overrode the output path.
- **Model configuration**: Groq via `langchain-groq`, created only in the config module. `.env` holds `GROQ_API_KEY` and `MODEL_NAME`, which starts **blank**; there is no fail-fast validation for the blank model — the model choice is deliberately deferred until after implementation.
- **Packaging**: `uv` with `pyproject.toml`; dependencies include langgraph, langchain-groq, langchain-community, ddgs, fastapi, uvicorn, python-dotenv, and the SQLite checkpointer package. `git init` plus a `.gitignore` covering `.env`, `data/`, and `runs/`; LangSmith tracing stays dormant, activatable purely through environment variables.

## Testing Decisions

- **One seam: the FastAPI HTTP boundary.** Tests act as ordinary API clients: they start Runs, poll status, resume Gates with Gate Decisions, and assert on HTTP responses plus files appearing under the Run's folder. Nothing internal (node functions, state internals, graph wiring) is tested directly.
- **The chat model is faked at the config layer.** A scripted fake chat model — canned plan, outline, draft, and critique responses with a controllable Verdict — is injected by overriding the config module's model factory, so tests need no Groq key and no network. The fake's script is what makes deterministic scenarios possible (e.g., "critique always says revise" to exercise the Revision cap).
- **Scenarios covered at this seam**: Run start and progress polling; Gate 1 pause payload and outline approve/revise routing; Verdict-driven revise loop and the 2-Revision cap with force-accept header note; Gate 2 approve → final file written (default and overridden paths); Artifact accumulation; resume across a server restart with a temporary SQLite checkpointer; error cases (unknown Run ID, malformed Gate Decision).
- **What makes a good test here**: it verifies externally observable behavior — HTTP responses, status transitions, files on disk — and never asserts on internal calls or implementation details, so the internals can be refactored freely.
- **Prior art**: none — greenfield. The established pattern will be pytest with FastAPI's test client and dependency overrides for config and the checkpointer (temporary SQLite file, temporary runs directory per test).

## Out of Scope

- Choosing the actual model (deliberately blank in `.env` until after implementation).
- Streaming/SSE or websocket responses; polling only.
- Any tool-registry or swap-abstraction layer for search tools; keyless tools are used directly.
- Authentication, authorization, rate limiting, or multi-tenant concerns.
- Publishing to external blog platforms; output is Markdown on disk.
- Automated scheduling or batch generation of posts.
- LangGraph Studio workflows or a CLI interface.
- Real Groq end-to-end tests; all automated tests use the fake model.

## Further Notes

- The domain language (Run, Brief, Artifact, Researcher, Research Notes, Outline, Draft, Critique, Verdict, Revision, Gate, Gate Decision, Checkpoint) is defined in `GLOSSARY.md` at the repo root; the spec uses those terms as defined there.
- This spec was produced from a completed design interview (three grilling rounds); all decisions above were explicitly confirmed by the developer, including the two corrections: no tool-registry abstraction, and `MODEL_NAME` blank with no validation.
- **Publishing blocker**: the issue tracker and triage label vocabulary have not been set up in this environment yet (`gh` CLI absent, repo not initialized). Run `/setup-matt-pocock-skills`, then this spec should be published to the tracker and labeled `ready-for-agent`.
