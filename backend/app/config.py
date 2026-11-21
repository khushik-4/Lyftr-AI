import os
# Force LiteLLM to use local model cost map and disable telemetry
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"

from typing import List, Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    LLM_API_KEYS: str = Field(
        default="mock_key_1,mock_key_2",
        description="Comma-separated API keys pool (at least 2 keys)"
    )
    LLM_MODEL: str = Field(
        default="gemini/gemini-2.0-flash",
        description="LiteLLM model identifier"
    )
    DATABASE_URL: str = Field(
        default="sqlite:///./data/app.db",
        description="SQLite database URL"
    )
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Allowed CORS origins comma-separated"
    )
    ENABLE_FAILURE_SIMULATION: bool = Field(
        default=True,
        description="Whether X-Simulate-Failure header is honored"
    )
    DEFAULT_SYSTEM_PROMPT: str = Field(
        default="You are Lyftr AI, a helpful, intelligent, and reliable conversational assistant.",
        description="Default system prompt if none is supplied"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_parsed_keys(self) -> List[Dict[str, str]]:
        """Parse LLM_API_KEYS preserving order and assigning key_1, key_2, etc."""
        raw_keys = [k.strip() for k in self.LLM_API_KEYS.split(",") if k.strip()]
        if len(raw_keys) < 2:
            # Fallback to ensure at least 2 keys exist if config is minimal
            if len(raw_keys) == 1:
                raw_keys.append("mock_fallback_key_2")
            else:
                raw_keys = ["mock_key_1", "mock_key_2"]
        return [{"id": f"key_{i+1}", "key": key} for i, key in enumerate(raw_keys)]

    def get_allowed_origins_list(self) -> List[str]:
        """Return list of allowed CORS origins, allowing '*' if specified."""
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        origins = [orig.strip() for orig in self.ALLOWED_ORIGINS.split(",") if orig.strip()]
        return origins if origins else ["*"]


settings = Settings()
