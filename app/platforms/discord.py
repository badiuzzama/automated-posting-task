"""Discord - Execute Webhook (https://discord.com/developers/docs/resources/webhook#execute-webhook)"""
import httpx

from app.platforms.base import Platform, PlatformError, Published


class DiscordPlatform(Platform):
    name = "Discord"
    required_settings = ("discord_webhook_url",)

    async def publish(self, message: str, client: httpx.AsyncClient) -> Published:
        hook = self.settings.discord_webhook_url
        resp = await client.post(hook, params={"wait": "true"}, json={"content": message})
        self.check(resp, "Discord post")
        data = resp.json()
        message_id, channel_id = data.get("id"), data.get("channel_id")
        if not message_id or not channel_id:
            raise PlatformError("Discord did not return a message id")

        guild_id = data.get("guild_id")
        if not guild_id:  # the webhook object knows which server it belongs to
            info = await client.get(hook)
            if info.is_success:
                guild_id = info.json().get("guild_id")
        guild = guild_id or "@me"
        # Discord message links need server membership, so they are never anonymously public.
        return Published(url=f"https://discord.com/channels/{guild}/{channel_id}/{message_id}", public=False)
