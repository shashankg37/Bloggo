"""Pipeline stages.

Ticket 02 ships only the pass-through Brief stage: a complete, if trivial,
vertical slice proving the graph → Checkpoint → API wiring. Later tickets
add plan, researcher, outline, draft, critic, gates, and publish here.
"""

from __future__ import annotations

from blog_agent.state import BlogState


def brief_stage(state: BlogState) -> dict:
    """Pass-through: the Brief flows into the Checkpoint unchanged."""
    return {}
