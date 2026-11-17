"""The agentic state: one typed schema flowing through the whole pipeline.

This is the single schema agreed in spec 0001 — no chat-message list; this
is a task pipeline, not a chatbot. Fields fill in as stages complete, so the
TypedDict is partial (`total=False`).

The two reducers: `research_notes` accumulates across research passes and
`critiques` records every Critique with its Verdict. Every other field is
owned by one stage.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class BlogState(TypedDict, total=False):
    # Brief (the input to a Run)
    topic: str
    audience: str
    tone: str
    target_words: int
    output_path: str

    # Plan (angle and research questions for the Researcher)
    plan: str

    # Research Notes (append reducer: accumulated across searches)
    research_notes: Annotated[list[str], operator.add]

    # Outline (subject to Gate 1 approval)
    outline: str
    outline_feedback: str

    # Draft loop
    draft: str
    critique: str  # the Critic's latest critique (drives redrafting)
    verdict: str  # "revise" | "approve"
    critiques: Annotated[list[dict], operator.add]  # {"critique": ..., "verdict": ...}
    revision_count: int
    outstanding_critique: str  # set when the cap force-accepts the last Draft

    # Output
    final_markdown: str

    # Run lifecycle (set by the executor when a stage crashes)
    error: str
