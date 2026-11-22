"""Telegram Bot API - sendMessage to a channel (https://core.telegram.org/bots/api#sendmessage)"""
import httpx

from app.platforms.base import Platform, PlatformError, Published


class TelegramPlatform(Platform):
    name = "Telegram"
    required_settings = ("telegram_bot_token", "telegram_chat_id")

    async def publish(self, message: str, client: httpx.AsyncClient) -> Published:
        s = self.settings
        resp = await client.post(
            f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
            json={"chat_id": s.telegram_chat_id, "text": message},
        )
        self.check(resp, "Telegram post")
        result = resp.json().get("result") or {}
        message_id = result.get("message_id")
        if message_id is None:
            raise PlatformError("Telegram did not return a message id")
        username = (result.get("chat") or {}).get("username")
        if username:  # public channel -> https://t.me/<channel>/<id>
            return Published(url=f"https://t.me/{username}/{message_id}")
        chat_id = str(result.get("chat", {}).get("id", ""))
        internal = chat_id[4:] if chat_id.startswith("-100") else chat_id.lstrip("-")
        return Published(url=f"https://t.me/c/{internal}/{message_id}", public=False)
