from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, HttpUrl


class Lead(BaseModel):
    """Normalized representation of an opportunity to respond."""

    id: str
    platform: str
    url: HttpUrl
    title: str
    text: str
    author: str
    score: Optional[int] = None
    followers: Optional[int] = None
    created_ts: float
    draft: Optional[str] = None
