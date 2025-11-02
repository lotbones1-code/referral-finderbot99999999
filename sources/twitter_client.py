from __future__ import annotations

import os
import time
from typing import AsyncGenerator

import httpx

from core.models import Lead
from core.matcher import IntentMatcher


class TwitterSource:
    """Fetch recent tweets that match keywords using the Twitter API v2."""

    def __init__(self, matcher: IntentMatcher):
        self.matcher = matcher
        self.bearer = os.getenv("TWITTER_BEARER_TOKEN")
        self.min_followers = int(os.getenv("MIN_FOLLOWERS", "25"))

    async def find_posts(self) -> AsyncGenerator[dict, None]:
        if not self.bearer:
            return

        query = '"new browser" OR "best browser" OR automation OR "AI agent" lang:en -is:retweet'
        params = {
            "query": query,
            "tweet.fields": "author_id,created_at,public_metrics",
            "expansions": "author_id",
            "user.fields": "public_metrics,username",
            "max_results": 50,
        }
        url = "https://api.twitter.com/2/tweets/search/recent"

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers={"Authorization": f"Bearer {self.bearer}"})
            if response.status_code != 200:
                return
            payload = response.json()
            users = {user["id"]: user for user in payload.get("includes", {}).get("users", [])}
            for tweet in payload.get("data", []):
                user = users.get(tweet["author_id"], {})
                text = tweet.get("text", "")
                if not self.matcher.match(text):
                    continue
                followers = user.get("public_metrics", {}).get("followers_count", 0)
                if followers < self.min_followers:
                    continue
                url = f"https://twitter.com/{user.get('username', '')}/status/{tweet['id']}"
                lead = Lead(
                    id=f"twitter_{tweet['id']}",
                    platform="twitter",
                    url=url,
                    title=text[:120],
                    text=text,
                    author=user.get("username", ""),
                    score=tweet.get("public_metrics", {}).get("like_count", 0),
                    followers=followers,
                    created_ts=time.time(),
                )
                yield lead.model_dump()
