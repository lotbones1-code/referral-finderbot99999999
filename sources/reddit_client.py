from __future__ import annotations

import asyncio
import os
import time
from typing import AsyncGenerator

import praw

from core.models import Lead
from core.matcher import IntentMatcher


class RedditSource:
    """Fetch matching Reddit submissions via PRAW search."""

    def __init__(self, matcher: IntentMatcher):
        self.matcher = matcher
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "referral-finder-bot/1.0"),
        )
        self.min_score = int(os.getenv("MIN_SCORE", "1"))
        self.subreddits = [
            "technology",
            "browsers",
            "Productivity",
            "selfhosted",
            "Automation",
            "InternetIsBeautiful",
        ]
        self.query = "(\"new browser\" OR \"best browser\" OR automation OR \"AI agent\")"

    async def find_posts(self) -> AsyncGenerator[dict, None]:
        loop = asyncio.get_event_loop()
        for subreddit in self.subreddits:
            submissions = await loop.run_in_executor(
                None,
                lambda s=subreddit: list(
                    self.reddit.subreddit(s).search(query=self.query, sort="new", limit=25)
                ),
            )
            for post in submissions:
                text = f"{post.title or ''}\n{post.selftext or ''}"
                if not self.matcher.match(text):
                    continue
                if post.score is not None and int(post.score) < self.min_score:
                    continue
                if not self.matcher.allowed(
                    "reddit",
                    str(post.author or ""),
                    post.url,
                    subreddit=str(post.subreddit or ""),
                ):
                    continue
                lead = Lead(
                    id=f"reddit_{post.id}",
                    platform="reddit",
                    url=post.url,
                    title=post.title or "",
                    text=post.selftext or "",
                    author=str(post.author or ""),
                    score=int(post.score or 0),
                    followers=None,
                    created_ts=float(getattr(post, "created_utc", time.time())),
                )
                yield lead.model_dump()
