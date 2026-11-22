"""GitHub Gist - POST /gists (https://docs.github.com/en/rest/gists/gists#create-a-gist)"""
import httpx

from app.platforms.base import Platform, Published


class GitHubGistPlatform(Platform):
    name = "GitHub Gist"
    required_settings = ("github_token",)

    async def publish(self, message: str, client: httpx.AsyncClient) -> Published:
        resp = await client.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"Bearer {self.settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "description": message[:100],
                "public": True,
                "files": {"post.md": {"content": message}},
            },
        )
        self.check(resp, "Gist creation")
        return Published(url=resp.json()["html_url"])
