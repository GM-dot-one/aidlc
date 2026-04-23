"""Settings / config validation tests."""

from __future__ import annotations

import pytest

from aidlc.config import LLMProvider, Settings


class TestSettings:
    def test_loads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENPROJECT_URL", "http://op.local:8080/")  # trailing slash
        monkeypatch.setenv("OPENPROJECT_API_KEY", "k")
        monkeypatch.setenv("GITHUB_REPO", "me/my-repo")
        s = Settings()  # type: ignore[call-arg]
        assert s.openproject_url == "http://op.local:8080"
        assert s.openproject_api_key.get_secret_value() == "k"
        assert s.github_repo == "me/my-repo"
        assert s.aidlc_llm_provider is LLMProvider.anthropic

    def test_rejects_malformed_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENPROJECT_API_KEY", "k")
        monkeypatch.setenv("GITHUB_REPO", "not-a-slash-repo")
        with pytest.raises(Exception, match="owner/repo"):
            Settings()  # type: ignore[call-arg]

    def test_require_anthropic_key_raises_when_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENPROJECT_API_KEY", "k")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        s = Settings()  # type: ignore[call-arg]
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            s.require_anthropic_key()

    def test_require_groq_key_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENPROJECT_API_KEY", "k")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        s = Settings()  # type: ignore[call-arg]
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            s.require_groq_key()

    def test_groq_provider_selectable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENPROJECT_API_KEY", "k")
        monkeypatch.setenv("AIDLC_LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_fake")
        s = Settings()  # type: ignore[call-arg]
        assert s.aidlc_llm_provider is LLMProvider.groq
        assert s.require_groq_key().get_secret_value() == "gsk_fake"

    def test_require_github_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENPROJECT_API_KEY", "k")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        s = Settings()  # type: ignore[call-arg]
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
            s.require_github()
