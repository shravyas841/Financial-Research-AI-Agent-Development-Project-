from pathlib import Path

from config.settings import get_settings
from data.database import Database


def test_default_cohere_configuration(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    monkeypatch.delenv("COHERE_MODEL", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.cohere_api_key == ""
    assert settings.cohere_model == "command-a-03-2025"
    get_settings.cache_clear()


def test_cohere_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("COHERE_API_KEY", "configured-key")
    monkeypatch.setenv("COHERE_MODEL", "custom-command-model")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.cohere_api_key == "configured-key"
    assert settings.cohere_model == "custom-command-model"
    get_settings.cache_clear()


def test_database_schema_does_not_store_cohere_key(tmp_path: Path):
    database = Database(tmp_path / "security.db")
    database.initialize()
    with database.connect() as connection:
        schema = " ".join(
            row["sql"] or ""
            for row in connection.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        ).lower()
    assert "cohere" not in schema
    assert "api_key" not in schema


def test_streamlit_state_does_not_store_cohere_key():
    source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8").lower()
    assert 'session_state["cohere' not in source
