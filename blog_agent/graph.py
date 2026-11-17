"""Graph topology: a fixed pipeline with conditional edges and Gates.

Ticket 02 wires the skeleton; ticket 03 extends the pipeline with the plan
and Researcher stages. The topology stays a readable, fixed pipeline; the
critique loop's conditional edge and the two interrupt Gates arrive in
later tickets.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from blog_agent import nodes, state


def build_graph(checkpointer: BaseCheckpointSaver):
    """Compile the Run pipeline with the given checkpointer."""
    builder = StateGraph(state.BlogState)
    builder.add_node("brief", nodes.brief_stage)
    builder.add_node("plan", nodes.plan_stage)
    builder.add_node("researcher", nodes.researcher_stage)
    builder.add_edge(START, "brief")
    builder.add_edge("brief", "plan")
    builder.add_edge("plan", "researcher")
    builder.add_edge("researcher", END)
    return builder.compile(checkpointer=checkpointer)
