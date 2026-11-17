"""Smoke test: the server boots and answers over the HTTP seam."""

from fastapi.testclient import TestClient

from blog_agent.api import app


def test_health_answers_over_http() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
