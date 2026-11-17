"""Entrypoint: run the API server with uvicorn.

    uv run python -m uvicorn blog_agent.main:app --reload
"""

import uvicorn

from blog_agent.api import app  # noqa: F401 — re-exported for the uvicorn command

if __name__ == "__main__":
    uvicorn.run("blog_agent.api:app", host="127.0.0.1", port=8000)
