"""Shared fixtures: settings-bound app, fake chat model, offline search."""

import pytest
from fastapi.testclient import TestClient

from blog_agent import config, tools
from blog_agent.api import create_app
from tests.fakes import ScriptedChatModel, scripted_tool


@pytest.fixture
def client(tmp_path):
    """The API against temporary checkpoint and runs locations."""
    settings = config.Settings(
        checkpoint_db=str(tmp_path / "checkpoints.sqlite"),
        runs_dir=str(tmp_path / "runs"),
    )
    with TestClient(create_app(settings=settings)) as test_client:
        yield test_client


@pytest.fixture
def fake_chat_model(monkeypatch):
    """Override the config chat-model factory with a scripted fake.

    Returns the fake so a test can script responses (plain content,
    AIMessages with tool calls, or Exceptions) before starting a Run.
    """
    from langchain_core.messages import AIMessage

    model = ScriptedChatModel(responses=[AIMessage(content="canned response")])
    monkeypatch.setattr(config, "create_chat_model", lambda: model)
    return model


@pytest.fixture
def offline_search(monkeypatch):
    """Replace the live keyless search tool with an offline stub."""
    stub = scripted_tool()
    monkeypatch.setattr(tools, "make_search_tool", lambda: stub)
    return stub
