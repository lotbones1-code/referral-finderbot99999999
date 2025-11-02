from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

import yaml


class IntentMatcher:
    """Keyword-based intent matcher with blacklist filtering."""

    def __init__(self, keywords_path: str, blacklist_path: str):
        self.keywords_path = Path(keywords_path)
        self.blacklist_path = Path(blacklist_path)
        self.config = yaml.safe_load(self.keywords_path.read_text(encoding="utf-8")) or {}
        self.blacklist = yaml.safe_load(self.blacklist_path.read_text(encoding="utf-8")) or {}
        self.include_patterns = self._compile_patterns(self.config.get("include", []))
        self.exclude_patterns = self._compile_patterns(self.config.get("exclude", []))

    @staticmethod
    def _compile_patterns(words: Iterable[str]) -> List[re.Pattern[str]]:
        return [re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in words]

    def match(self, text: str) -> bool:
        if not text:
            return False
        for pattern in self.exclude_patterns:
            if pattern.search(text):
                return False
        return any(pattern.search(text) for pattern in self.include_patterns)

    def allowed(self, platform: str, author: str, url: str, **metadata: object) -> bool:
        domains = set(self.blacklist.get("domains", []) or [])
        users = set(self.blacklist.get("users", []) or [])
        subreddits = set(self.blacklist.get("subreddits", []) or [])
        if any(domain in (url or "") for domain in domains):
            return False
        if author and author in users:
            return False
        subreddit = (metadata.get("subreddit") or "").lower() if metadata else ""
        if subreddit and subreddit in {s.lower() for s in subreddits}:
            return False
        return True
