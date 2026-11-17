"""Test doubles for the HTTP seam.

The scripted fake chat model stands in for the real provider so tests need
no API key and no network. Both are injected by overriding:
- `blog_agent.config.create_chat_model` — the scripted chat model
- `blog_agent.tools.make_search_tool` — a stub search tool

An `Exception` entry in the script makes the model raise, for Run error-path
tests.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool


def scripted_model(*responses: str) -> FakeListChatModel:
    """A chat model that replies with canned responses in turn, then cycles."""
    return FakeListChatModel(responses=list(responses))


class ScriptedChatModel(BaseChatModel):
    """Replies with canned messages in turn, then repeats the last.

    Unlike `FakeListChatModel`, entries may be `AIMessage`s carrying
    tool_calls (for driving the Researcher's tool loop) or `Exception`s
    (for error-path tests). `bind_tools` is a no-op: the script decides what
    the model does, so tool schemas never reach a live provider.
    """

    responses: list  # BaseMessage | Exception
    step: int = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        entry = self.responses[min(self.step, len(self.responses) - 1)]
        self.step += 1
        if isinstance(entry, Exception):
            raise entry
        return ChatResult(generations=[ChatGeneration(message=entry)])

    @property
    def _llm_type(self) -> str:
        return "scripted-chat-model"

    def bind_tools(self, tools, **kwargs):
        return self


def scripted_tool(result: str = "stub search results"):
    """A keyless, offline stand-in for the web search tool."""

    @tool("web_search")
    def web_search(query: str) -> str:
        """Search the web for real material (stubbed offline in tests)."""
        return f"{result}: {query}"

    return web_search
