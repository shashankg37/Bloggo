"""The config layer is the fake-model injection point (ticket 01)."""

from blog_agent import config
from tests.fakes import scripted_model


def test_chat_model_factory_is_overridable(monkeypatch) -> None:
    model = scripted_model("an outline")
    monkeypatch.setattr(config, "create_chat_model", lambda: model)

    assert config.create_chat_model() is model


def test_blank_model_name_is_accepted() -> None:
    """MODEL_NAME starts blank in .env; the config accepts it without error."""
    settings = config.Settings()

    assert settings.model_name == ""
