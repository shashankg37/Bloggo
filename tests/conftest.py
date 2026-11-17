"""Shared fixtures: the fake chat model injected at the config layer."""

import pytest

from blog_agent import config
from tests.fakes import scripted_model


@pytest.fixture
def fake_chat_model(monkeypatch: pytest.MonkeyPatch):
    """Override the config chat-model factory with a scripted fake.

    Returns the fake so a test can inspect what the graph asked of it.
    """
    model = scripted_model("canned response")
    monkeypatch.setattr(config, "create_chat_model", lambda: model)
    return model
