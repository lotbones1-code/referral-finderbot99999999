from __future__ import annotations

import re
import time
from typing import AsyncGenerator, Iterable

import httpx

from core.models import Lead
from core.matcher import IntentMatcher


FEEDS = [
    "https://news.google.com/rss/search?q=\"new+browser\"+OR+\"best+browser\"+OR+automation+OR+\"AI+agent\"&hl=en-US&gl=US&ceid=US:en"
]


class RSSSource:
    """Fetch articles from configured RSS feeds."""

    def __init__(self, matcher: IntentMatcher, feeds: Iterable[str] | None = None):
        self.matcher = matcher
        self.feeds = list(feeds or FEEDS)

    async def find_posts(self) -> AsyncGenerator[dict, None]:
        async with httpx.AsyncClient(timeout=15) as client:
            for feed in self.feeds:
                response = await client.get(feed)
                if response.status_code != 200:
                    continue
                for item in re.finditer(r"<item>(.*?)</item>", response.text, flags=re.IGNORECASE | re.DOTALL):
                    chunk = item.group(1)
                    title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", chunk)
                    link_match = re.search(r"<link>(.*?)</link>", chunk)
                    title = title_match.group(1) if title_match else ""
                    link = link_match.group(1) if link_match else ""
                    if not self.matcher.match(title):
                        continue
                    lead = Lead(
                        id=f"rss_{hash(link)}",
                        platform="rss",
                        url=link,
                        title=title,
                        text=title,
                        author="rss",
                        score=None,
                        followers=None,
                        created_ts=time.time(),
                    )
                    yield lead.model_dump()
