# 01: Scaffold, config, and server skeleton

**What to build:** A bootable blog-writing-agent server as a uv-managed Python package: git initialized with a `.gitignore` covering `.env`, the checkpoint database folder, and Run output folders; `.env` holding `GROQ_API_KEY` and a deliberately blank `MODEL_NAME` (no validation on the blank model); a config module that reads `.env` and creates the chat model through a single overridable factory (the spec's fake-model injection point); the FastAPI app bootable from the entrypoint; pytest wired with the scripted fake chat model, driven through the HTTP seam. This is the prefactor ticket: make the change easy.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Dependencies install and the server boots and answers an HTTP request
- [x] A git repo exists with the initial commit, and `.env`, checkpoint data, and Run output folders are ignored
- [x] The config module reads `.env` and exposes the chat-model factory; blank `MODEL_NAME` is accepted without error at boot
- [x] The scripted fake chat model can be injected by overriding the config layer; tests need no API key and no network
- [x] A smoke test passes through the HTTP seam

**Notes:** Smart App Control on this machine blocks the compiled `xxhash` and `ormsgpack` DLLs; both are covered by pure-Python compat shims that activate only when the real extension cannot load, verified by round-trip tests through LangGraph's own checkpoint serializer. Run commands must use the `uv run python -m ...` form (the `.venv\Scripts` exes are blocked by the same policy).
