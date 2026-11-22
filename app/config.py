"""Application settings, loaded from environment variables / a local .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Mastodon
    mastodon_instance_url: str | None = None
    mastodon_access_token: str | None = None
    # Bluesky
    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None
    # Telegram
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    # DEV Community
    devto_api_key: str | None = None
    # GitHub Gist
    github_token: str | None = None
    # Discord
    discord_webhook_url: str | None = None

    # Behaviour
    platform_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
