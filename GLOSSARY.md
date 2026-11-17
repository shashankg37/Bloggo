# Blog Writing Agent

A LangGraph-based agent that turns a topic into a finished Markdown blog post through a plan → research → outline → draft → critique pipeline, pausing for human approval at defined gates.

## Language

### Run

**Run**:
One execution of the pipeline for a single topic, identified by a thread ID and backed by a persisted checkpoint.
_Avoid_: session, job, task

**Brief**:
The input to a Run: topic plus optional audience, tone, and target word count.
_Avoid_: prompt, request, config

**Artifact**:
A Markdown file written to disk during a Run (research, outline, draft, final post), representing the state at that stage.
_Avoid_: output, dump, log

### Pipeline stages

**Research Notes**:
The accumulated findings the Researcher gathered via web search, stored in state and used by later stages.
_Avoid_: search results, sources, context

**Researcher**:
The tool-calling agent node that decides when to search the web and what to record, capped at a fixed number of searches per Run.
_Avoid_: search node, scraper

**Outline**:
The pre-draft structure of the post: sections with headings and a short description of each, subject to human approval.
_Avoid_: plan, skeleton, TOC

**Draft**:
A full written version of the post produced from the approved Outline and Research Notes. Multiple Drafts may exist across revisions; the current one lives in state.
_Avoid_: post, article, copy

**Critique**:
The Critic's structured assessment of the current Draft: problems found plus a Verdict.
_Avoid_: review, feedback (unqualified), rating

**Critic**:
The node that evaluates a Draft against the Brief and the Outline and returns a Critique.
_Avoid_: reviewer, judge, grader

**Verdict**:
The Critic's decision enum: `revise` or `approve`.
_Avoid_: status, score, result

**Revision**:
One pass of critique → redraft. A Run's loop is capped at 2 Revisions, after which the last Draft is force-accepted and the outstanding Critique is noted in the final file header.
_Avoid_: iteration, retry, loop

### Human gates

**Gate**:
A point in the graph where the Run pauses (LangGraph interrupt) and waits for a human decision before continuing.
_Avoid_: checkpoint, stop, halt

**Gate Decision**:
The human's response to a Gate: approve (continue) or revise (with feedback fed back into state).
_Avoid_: resume payload, input, response

### Persistence

**Checkpoint**:
The persisted snapshot of the agent state for a Run, stored in the SQLite checkpointer, enabling pause/resume across processes.
_Avoid_: save, snapshot (in user-facing language), backup
