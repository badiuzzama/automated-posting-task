"""Helpers for finding and validating links inside a message."""
import re
from urllib.parse import urlparse

# Anything that looks like a link: "<scheme>://..." or "www...."
_CANDIDATE_RE = re.compile(r"(?:[a-zA-Z][a-zA-Z0-9+.\-]*://|www\.)\S+")
_TRAILING_PUNCTUATION = ".,;:!?)]}>'\""
_HOST_RE = re.compile(
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", re.IGNORECASE
)


def find_links(text: str) -> list[str]:
    """Return every link-like token in ``text`` with trailing punctuation removed."""
    return [m.group(0).rstrip(_TRAILING_PUNCTUATION) for m in _CANDIDATE_RE.finditer(text)]


def link_error(url: str) -> str | None:
    """Return a human readable problem with ``url``, or ``None`` if it is valid."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "The CTA link must start with http:// or https://."
    try:
        parsed.port  # noqa: B018 - raises ValueError on a bad port
    except ValueError:
        return "The CTA link has an invalid port."
    host = parsed.hostname
    if not host or not _HOST_RE.fullmatch(host):
        return "The CTA link has an invalid domain name."
    return None


def strip_links(text: str) -> str:
    """Return ``text`` with link tokens removed and whitespace collapsed."""
    for link in find_links(text):
        text = text.replace(link, " ")
    return " ".join(text.split())
