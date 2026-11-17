"""Graph topology: a fixed pipeline with conditional edges and Gates.

Ticket 02 wires the skeleton: START → brief → END, compiled with a
checkpointer so every Run persists its state. Later tickets extend this
module with the real stages, the critique loop's conditional edge, and the
two interrupt Gates — the topology stays a readable, fixed pipeline.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from blog_agent import nodes, state


def build_graph(checkpointer: BaseCheckpointSaver):
    """Compile the Run pipeline with the given checkpointer."""
    builder = StateGraph(state.BlogState)
    builder.add_node("brief", nodes.brief_stage)
    builder.add_edge(START, "brief")
    builder.add_edge("brief", END)
    return builder.compile(checkpointer=checkpointer)
