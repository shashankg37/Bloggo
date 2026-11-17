"""Test doubles for the HTTP seam.

The scripted fake chat model stands in for the real provider so tests need
no API key and no network. It is injected by overriding
`blog_agent.config.create_chat_model` (see spec 0001, Testing Decisions).
"""

from langchain_core.language_models.fake_chat_models import FakeListChatModel


def scripted_model(*responses: str) -> FakeListChatModel:
    """A chat model that replies with canned responses in turn, then cycles."""
    return FakeListChatModel(responses=list(responses))
