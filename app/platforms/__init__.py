from app.config import Settings
from app.platforms.base import Platform, PlatformError, Published
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.github_gist import GitHubGistPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform

ALL_PLATFORMS: tuple[type[Platform], ...] = (
    MastodonPlatform,
    BlueskyPlatform,
    TelegramPlatform,
    DevToPlatform,
    GitHubGistPlatform,
    DiscordPlatform,
)


def build_platforms(settings: Settings) -> list[Platform]:
    return [cls(settings) for cls in ALL_PLATFORMS]


__all__ = ["Platform", "PlatformError", "Published", "build_platforms", "ALL_PLATFORMS"]
