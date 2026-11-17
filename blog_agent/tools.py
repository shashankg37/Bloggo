"""Keyless research tools for the Researcher (spec 0001: no API keys).

The DuckDuckGo search tool from the LangChain community ecosystem runs
keyless via the `ddgs` package. It is a plain factory, not a registry:
tests substitute a stub here, and nothing else.
"""

from __future__ import annotations

from langchain_community.tools import DuckDuckGoSearchRun


def make_search_tool():
    """The keyless web search tool the Researcher is bound to."""
    return DuckDuckGoSearchRun()
