"""configuration for plyrfm client."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """plyrfm configuration.

    environment variables:
        PLYR_TOKEN: API token for authenticated operations (required for uploads/deletes)
        PLYR_API_URL: API base URL (default: https://api.plyr.fm)

    example:
        export PLYR_TOKEN="your_token_here"
        plyr list
    """

    model_config = SettingsConfigDict(
        env_prefix="PLYR_",
        env_file=".env",
        extra="ignore",
    )

    token: str | None = Field(
        default=None,
        description="developer token for authenticated operations",
    )
    api_url: str = Field(
        default="https://api.plyr.fm",
        description="API base URL",
    )

    @property
    def auth_headers(self) -> dict[str, str]:
        """get authorization headers. raises if no token configured."""
        if not self.token:
            msg = (
                "PLYR_TOKEN not set. "
                "create a token at plyr.fm/portal -> 'developer tokens'"
            )
            raise ValueError(msg)
        return {"Authorization": f"Bearer {self.token}"}


@lru_cache
def get_settings() -> Settings:
    """get cached settings instance."""
    return Settings()
