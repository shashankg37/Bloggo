# 03: Researcher stage — real research with keyless tools

**What to build:** The front of the pipeline does real work: a plan stage turns the Brief into research guidance, then the Researcher — a real tool-calling agent (a prebuilt react subgraph) bound to keyless DuckDuckGo search from the LangChain community ecosystem — gathers material, bounded to roughly three searches per Run. Research Notes accumulate in state via an explicit append reducer, land as a `research.md` Artifact, and `GET /runs/{id}/artifacts` lists and serves Artifacts. Status shows stage progression from plan to researcher.

**Blocked by:** 02: Run lifecycle basics

**Status:** ready-for-agent

- [ ] Status shows the Run progressing through plan then researcher stages
- [ ] The Researcher is a tool-calling agent using the keyless DuckDuckGo search tool (no API key)
- [ ] Research is bounded to roughly three searches per Run
- [ ] Research Notes accumulate in state via the append reducer across multiple searches
- [ ] A research notes Artifact is written for the Run
- [ ] The artifacts endpoint lists and serves the Run's Artifacts
- [ ] Tests script the fake chat model to make tool calls and substitute a stub search tool so no live network is used; the reducer accumulation and search cap are verified through the HTTP seam
