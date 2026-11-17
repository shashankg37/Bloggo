"""FastAPI application for the blog-writing agent.

Ticket 02 adds the Run lifecycle (`POST /runs`, `GET /runs/{id}`, ...);
for now the app proves the server boots and answers over the HTTP seam.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Blog Writing Agent",
    description="Topic in, Markdown post out, with human Gates and durable Runs.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: the server is up."""
    return {"status": "ok"}
