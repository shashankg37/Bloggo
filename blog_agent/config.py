"""Configuration for the blog-writing agent.

Reads `.env` at import time and owns the chat-model factory — the single
place where the LLM is created, so swapping provider or model is a one-line
change (spec 0001). Tests inject the scripted fake chat model by overriding
`create_chat_model` on this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Everything the agent reads from the environment."""

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    # Deliberately blank until after the build; no fail-fast validation (spec 0001).
    model_name: str = os.getenv("MODEL_NAME", "")
    checkpoint_db: str = os.getenv("CHECKPOINT_DB", "data/checkpoints.sqlite")
    runs_dir: str = os.getenv("RUNS_DIR", "runs")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def create_chat_model():
    """Create the chat model the graph will use.

    Imported lazily so that importing this module (and thus booting the
    server) never requires a Groq API key — tests override this factory with
    the scripted fake before any model is created.
    """
    from langchain_groq import ChatGroq

    settings = get_settings()
    return ChatGroq(
        model=settings.model_name,
        api_key=settings.groq_api_key or None,
        temperature=0.4,
    )
