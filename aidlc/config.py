"""Runtime configuration, loaded from environment / .env.

Uses pydantic-settings so that every string passes through a typed,
validated surface. Secrets are wrapped in ``SecretStr`` so that
``repr(Settings())`` does not leak them in logs or tracebacks.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# StrEnum lands in 3.11. Our supported range is 3.11+ per pyproject, but the
# shim lets tooling that only has 3.10 (e.g. old CI runners) still import.
if sys.version_info >= (3, 11):  # noqa: UP036 — intentional runtime fallback for 3.10
    from enum import StrEnum
else:  # pragma: no cover - 3.10 fallback
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]  # noqa: UP042
        pass


class LLMProvider(StrEnum):
    """Supported LLM backends. Extend by adding an adapter in ``aidlc.llm``."""

    anthropic = "anthropic"
    groq = "groq"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Top-level agent configuration.

    Reads from environment variables first, then from ``.env`` in CWD. Fields
    without sensible defaults raise at import time so we fail fast rather than
    discovering a missing API key mid-workflow.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- OpenProject ---------------------------------------------------------
    openproject_url: str = Field(default="http://localhost:8080")
    openproject_api_key: SecretStr = Field(...)
    openproject_project: str = Field(default="ai-dlc-demo")

    # --- LLM -----------------------------------------------------------------
    aidlc_llm_provider: LLMProvider = Field(default=LLMProvider.anthropic)
    anthropic_api_key: SecretStr | None = Field(default=None)
    anthropic_model: str = Field(default="claude-sonnet-4-6")
    # Groq is OpenAI-compatible; free tier is generous for this POC.
    # See https://console.groq.com/docs/models for current model IDs.
    groq_api_key: SecretStr | None = Field(default=None)
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # --- GitHub --------------------------------------------------------------
    github_token: SecretStr | None = Field(default=None)
    github_repo: str | None = Field(default=None, description="owner/repo")
    github_base_branch: str = Field(default="main")

    # --- Runtime -------------------------------------------------------------
    aidlc_db_path: Path = Field(default=Path(".aidlc/state.db"))
    aidlc_workdir: Path = Field(default=Path(".aidlc/workdir"))
    aidlc_log_level: LogLevel = Field(default=LogLevel.INFO)

    # --- Claude Code (local code-generation agent) ---------------------------
    # Path to the `claude` CLI. Override if it's not on PATH or you use npx.
    claude_code_model: str = Field(default="claude-sonnet-4-6")
    claude_code_bin: str = Field(default="claude")
    # Permission mode for headless runs: default | acceptEdits | bypassPermissions | plan
    # bypassPermissions lets Claude run tests and bash without prompting.
    claude_code_permission_mode: str = Field(default="bypassPermissions")
    # Cap agent loops so a runaway session can't eat all your tokens.
    claude_code_max_turns: int = Field(default=40)
    # Hard timeout per task (seconds).
    claude_code_timeout_s: int = Field(default=1800)

    @field_validator("openproject_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("github_repo")
    @classmethod
    def _validate_repo(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if "/" not in v or v.count("/") != 1:
            raise ValueError("GITHUB_REPO must be of the form 'owner/repo'")
        return v

    # Convenience ------------------------------------------------------------

    def require_anthropic_key(self) -> SecretStr:
        if self.anthropic_api_key is None:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; required when AIDLC_LLM_PROVIDER=anthropic"
            )
        return self.anthropic_api_key

    def require_groq_key(self) -> SecretStr:
        if self.groq_api_key is None:
            raise RuntimeError("GROQ_API_KEY is not set; required when AIDLC_LLM_PROVIDER=groq")
        return self.groq_api_key

    def require_github(self) -> tuple[SecretStr, str]:
        if self.github_token is None or self.github_repo is None:
            raise RuntimeError(
                "GITHUB_TOKEN and GITHUB_REPO must both be set to run task_to_code / status_updates"
            )
        return self.github_token, self.github_repo


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Module-level singleton. Tests override by calling ``get_settings.cache_clear()``."""
    return Settings()  # pydantic-settings reads values from env
