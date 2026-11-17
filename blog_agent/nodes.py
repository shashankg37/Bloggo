"""Pipeline stages.

Ticket 03 adds the plan stage (angle + research questions for the Brief)
and the Researcher: a real tool-calling agent — a prebuilt react subgraph —
bound to keyless search tools, bounded to a fixed number of searches per
Run. Research Notes accumulate in state via the append reducer and land as
an Artifact on disk.

Stages receive the LangGraph `RunnableConfig` as their second argument;
`configurable` carries the thread_id and the Run's artifact root.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt

from blog_agent import config as app_config
from blog_agent.state import BlogState
from blog_agent.tools import make_search_tool

SEARCHES_PER_RUN = 3
# Each search round costs a model step plus a tool step; headroom for the
# final answer. A researcher that keeps searching hits this ceiling.
_RESEARCHER_RECURSION_LIMIT = SEARCHES_PER_RUN * 3 + 3


def _runs_root(run_config: RunnableConfig) -> Path:
    configurable = run_config["configurable"]
    return Path(configurable["runs_dir"]) / configurable["thread_id"]


def write_artifact(run_config: RunnableConfig, filename: str, content: str) -> Path:
    """Persist a stage's Artifact under the Run's folder."""
    path = _runs_root(run_config) / filename
    path.write_text(content, encoding="utf-8")
    return path


def brief_stage(state: BlogState) -> dict:
    """Pass-through: the Brief flows into the Checkpoint unchanged."""
    return {}


def plan_stage(state: BlogState, config: RunnableConfig) -> dict:
    """Turn the Brief into an angle and search queries for the Researcher."""
    model = app_config.create_chat_model()
    prompt = (
        "You are planning a blog post.\n"
        f"Topic: {state['topic']}\n"
        f"Audience: {state.get('audience', 'general readers')}\n"
        f"Tone: {state.get('tone', 'conversational')}\n"
        f"Target length: {state.get('target_words', 800)} words.\n\n"
        "Write a short plan: the angle this post should take, and exactly "
        "three web-search queries that would ground it in real material. "
        "Reply with the plan text only."
    )
    response = model.invoke([HumanMessage(content=prompt)])
    return {"plan": response.text}


def researcher_stage(state: BlogState, config: RunnableConfig) -> dict:
    """Research the topic with a tool-calling agent and record the Notes."""
    model = app_config.create_chat_model()
    researcher = create_react_agent(
        model,
        [make_search_tool()],
        prompt=(
            "You are a research agent gathering real material for a blog "
            f"post. Search at most {SEARCHES_PER_RUN} times, then write "
            "concise markdown research notes: bullet-point findings with the "
            "sources they came from."
        ),
    )
    research_brief = (
        f"Topic: {state['topic']}\n"
        f"Audience: {state.get('audience', 'general readers')}\n\n"
        f"Writing plan:\n{state.get('plan', '')}\n\n"
        f"Research this topic now."
    )
    result = researcher.invoke(
        {"messages": [HumanMessage(content=research_brief)]},
        {"recursion_limit": _RESEARCHER_RECURSION_LIMIT},
    )
    notes = result["messages"][-1].text
    write_artifact(config, "research.md", notes)
    return {"research_notes": [notes]}


def outline_stage(state: BlogState, config: RunnableConfig) -> dict:
    """Draft the Outline from the Brief, plan, and Research Notes.

    Re-runs after a Gate revision: the human's feedback drives a fresh pass.
    """
    model = app_config.create_chat_model()
    revision_note = (
        "The human rejected the previous outline with this feedback; "
        f"incorporate it fully:\n{state.get('outline_feedback', '')}\n\n"
        if state.get("outline_feedback")
        else ""
    )
    prompt = (
        "You are structuring a blog post.\n"
        f"Topic: {state['topic']}\n"
        f"Audience: {state.get('audience', 'general readers')}\n"
        f"Tone: {state.get('tone', 'conversational')}\n"
        f"Target length: {state.get('target_words', 800)} words.\n\n"
        f"Writing plan:\n{state.get('plan', '')}\n\n"
        f"Research notes:\n{'\n'.join(state.get('research_notes', []))}\n\n"
        f"{revision_note}"
        "Write the outline: markdown headings for each section, each with a "
        "one-sentence description of what it covers. Reply with the outline "
        "text only."
    )
    response = model.invoke([HumanMessage(content=prompt)])
    outline = response.text
    write_artifact(config, "outline.md", outline)
    return {"outline": outline}


def outline_gate(state: BlogState) -> dict:
    """Gate 1: pause the Run for the human's Gate Decision on the Outline.

    LangGraph re-executes this node on resume, and `interrupt` then returns
    the decision payload sent via the API:
    `{"decision": "approve"}` or `{"decision": "revise", "feedback": "..."}`.
    Routing keys off feedback presence (see ADR 0001): empty = approved.
    """
    decision = interrupt({"gate": "outline", "outline": state.get("outline", "")})
    if decision.get("decision") == "revise":
        return {"outline_feedback": decision.get("feedback", "")}
    return {"outline_feedback": ""}


def route_after_outline_gate(state: BlogState):
    """Revise feedback routes back to the Outline; approval moves on."""
    if state.get("outline_feedback"):
        return "outline"
    return END  # ticket 05: → draft
