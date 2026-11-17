# 03: Researcher stage — real research with keyless tools

**What to build:** The front of the pipeline does real work: a plan stage turns the Brief into research guidance, then the Researcher — a real tool-calling agent (a prebuilt react subgraph) bound to keyless DuckDuckGo search from the LangChain community ecosystem — gathers material, bounded to roughly three searches per Run. Research Notes accumulate in state via an explicit append reducer, land as a `research.md` Artifact, and `GET /runs/{id}/artifacts` lists and serves Artifacts. Status shows stage progression from plan to researcher.

**Blocked by:** 02: Run lifecycle basics

**Status:** done

- [x] Status shows the Run progressing through plan then researcher stages
- [x] The Researcher is a tool-calling agent using the keyless DuckDuckGo search tool (no API key)
- [x] Research is bounded to roughly three searches per Run
- [x] Research Notes accumulate in state via the append reducer across multiple searches
- [x] A research notes Artifact is written for the Run
- [x] The artifacts endpoint lists and serves the Run's Artifacts
- [x] Tests script the fake chat model to make tool calls and substitute a stub search tool so no live network is used; the reducer accumulation and search cap are verified through the HTTP seam

**Notes:** The fake chat model (`ScriptedChatModel`) scripts full AIMessages including tool calls, and stages call the model factory through the config module so the injection reaches them. The real keyless search was verified once manually (live DuckDuckGo results, no API key); automated tests stay offline. `create_react_agent` is deprecated in LangGraph V1 in favor of `langchain.agents.create_agent` — kept as-is since it works and is the LangGraph-native pattern; revisit if a LangGraph V2 upgrade happens.
