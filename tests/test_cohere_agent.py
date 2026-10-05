import json
from types import SimpleNamespace

import httpx
import pytest
from cohere.errors import InvalidTokenError, ServiceUnavailableError, TooManyRequestsError

from ai.research_agent import AIAnalysisError, AIConfigurationError, generate_research_analysis
from test_snapshot_ai import snapshot, valid_analysis


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.chat_kwargs = None

    def chat(self, **kwargs):
        self.chat_kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def response_with_text(text):
    return SimpleNamespace(message=SimpleNamespace(content=[SimpleNamespace(text=text)]))


def install_client(monkeypatch, client, captured):
    def factory(**kwargs):
        captured.update(kwargs)
        return client

    monkeypatch.setattr("ai.research_agent.cohere.ClientV2", factory)


def test_successful_cohere_response_is_validated_and_grounded(monkeypatch):
    expected = valid_analysis()
    client = FakeClient(response_with_text(expected.model_dump_json()))
    captured = {}
    install_client(monkeypatch, client, captured)

    result = generate_research_analysis(snapshot(), "cohere-test-key", "command-a-03-2025", 12)

    assert result == expected
    assert captured == {"api_key": "cohere-test-key", "timeout": 12, "max_retries": 1}
    assert client.chat_kwargs["model"] == "command-a-03-2025"
    assert client.chat_kwargs["response_format"]["type"] == "json_object"
    assert "ResearchSnapshot JSON" in client.chat_kwargs["messages"][1]["content"]
    assert "cohere-test-key" not in json.dumps(client.chat_kwargs)


@pytest.mark.parametrize("text", ["not json", '{"summary": "missing required fields"}'])
def test_malformed_cohere_response_is_rejected(monkeypatch, text):
    client = FakeClient(response_with_text(text))
    install_client(monkeypatch, client, {})
    with pytest.raises(AIAnalysisError, match="invalid structured analysis"):
        generate_research_analysis(snapshot(), "test-key", "command-a-03-2025")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (httpx.TimeoutException("timeout"), "timed out"),
        (TooManyRequestsError(body={"message": "limited"}), "rate limit"),
        (ServiceUnavailableError(body={"message": "down"}), "currently unavailable"),
    ],
)
def test_cohere_provider_failures_are_safe(monkeypatch, error, message):
    client = FakeClient(error=error)
    install_client(monkeypatch, client, {})
    with pytest.raises(AIAnalysisError, match=message):
        generate_research_analysis(snapshot(), "super-secret-key", "command-a-03-2025")


def test_cohere_cannot_invent_unavailable_pe(monkeypatch):
    bad = valid_analysis(fundamental_analysis="The P/E ratio is 24.5.")
    client = FakeClient(response_with_text(bad.model_dump_json()))
    install_client(monkeypatch, client, {})
    with pytest.raises(AIAnalysisError, match="P/E"):
        generate_research_analysis(snapshot(), "test-key", "command-a-03-2025")


def test_invalid_cohere_key_has_safe_error(monkeypatch):
    client = FakeClient(error=InvalidTokenError(body={"message": "invalid"}))
    install_client(monkeypatch, client, {})
    with pytest.raises(AIConfigurationError, match="rejected") as error:
        generate_research_analysis(snapshot(), "private-invalid-key", "command-a-03-2025")
    assert "private-invalid-key" not in str(error.value)


def test_api_key_is_not_logged_on_provider_failure(monkeypatch, caplog):
    client = FakeClient(error=ServiceUnavailableError(body={"message": "down"}))
    install_client(monkeypatch, client, {})
    with pytest.raises(AIAnalysisError):
        generate_research_analysis(snapshot(), "never-log-this-key", "command-a-03-2025")
    assert "never-log-this-key" not in caplog.text
