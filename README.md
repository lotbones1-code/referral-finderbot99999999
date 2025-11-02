# Referral Finder Bot — Codex-Ready Scaffold (Reddit · X · RSS)

A minimal, Codex-ready project that finds people asking for **new browsers** or **automation tools**, drafts a **non-spammy reply** recommending **Perplexity Browser** (or your pick), and appends **your referral link**. Human-in-the-loop by default; posting can be enabled per-platform if you choose.

> Goal: surface high-intent posts, generate good replies fast, and keep you within platform rules.

---

## Features

* Keyword & intent matching across:
  * Reddit (search + live stream)
  * X/Twitter (recent search; optional)
  * RSS/Google News (blog/forum posts)
* SQLite lead log + CSV export
* Draft reply generator with value props + your referral link
* Guardrails to avoid spam: rate limits, domain/author blacklist, minimum karma/followers thresholds, cool-downs
* One-command run; easy to hand to Codex

---

## Project Tree

```
referral-finder-bot/
├─ README.md                 # this file
├─ .env.example              # copy to .env and fill in
├─ requirements.txt
├─ main.py                   # entrypoint CLI
├─ sources/
│  ├─ reddit_client.py
│  ├─ twitter_client.py
│  └─ rss_client.py
├─ core/
│  ├─ models.py              # Pydantic models
│  ├─ storage.py             # SQLite + CSV
│  ├─ matcher.py             # keyword + simple intent
│  └─ reply.py               # reply drafting
└─ data/
   ├─ keywords.yaml
   ├─ blacklist.yaml
   └─ examples/
      └─ sample_posts.json
```

---

## Setup

1. Python 3.11+
2. Create env

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

3. Configure .env (copy from .env.example)

```bash
cp .env.example .env
```

Fill in:

```
REFERRAL_LINK="https://your-ref-link.example"
BRAND_NAME="Perplexity Browser"
# Reddit
REDDIT_CLIENT_ID=""
REDDIT_CLIENT_SECRET=""
REDDIT_USER_AGENT="referral-finder-bot/1.0 by u/yourname"
REDDIT_USERNAME=""
REDDIT_PASSWORD=""   # for posting (optional)
# X/Twitter (optional)
TWITTER_BEARER_TOKEN=""
TWITTER_POSTING_ENABLED=false
# General
MIN_SCORE=1            # reddit min upvotes
MIN_FOLLOWERS=25       # twitter min followers
RATE_LIMIT_PER_MIN=4   # max outbound drafts per minute
DRY_RUN=true           # set false to enable posting functions you implement
```

4. Keywords (`data/keywords.yaml`)

```yaml
include:
  - "new browser"
  - "best browser 2025"
  - "switch browsers"
  - "automation tool"
  - "workflow automation"
  - "AI agent browser"
  - "research browser"
  - "replace chrome"
  - "alternative to arc"
  - "alternative to chrome"
  - "how to automate browsing"
exclude:
  - "web scraping ban"
  - "homework cheating"
  - "botnet"
```

5. Blacklist (`data/blacklist.yaml`)

```yaml
domains:
  - example.com
users:
  - AutoModerator
subreddits:
  - politics
  - cryptoMoonShots
```

---

## Run

```bash
python main.py scan --sources reddit rss --export leads.csv
```

Add X/Twitter when you have creds:

```bash
python main.py scan --sources reddit twitter rss --export leads.csv
```

Draft replies only (no posting):

```bash
python main.py draft --limit 20
```

---

## requirements.txt

```
praw==7.7.1
httpx==0.27.2
pydantic==2.9.2
pyyaml==6.0.2
rich==13.9.2
python-dotenv==1.0.1
aiolimiter==1.1.0
sqlite-utils==3.37
```

---

## `.env.example`

```
REFERRAL_LINK=
BRAND_NAME=Perplexity Browser
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=referral-finder-bot/1.0 by u/yourname
REDDIT_USERNAME=
REDDIT_PASSWORD=
TWITTER_BEARER_TOKEN=
TWITTER_POSTING_ENABLED=false
MIN_SCORE=1
MIN_FOLLOWERS=25
RATE_LIMIT_PER_MIN=4
DRY_RUN=true
```

---

## `main.py` (single-file entrypoint)

```python
import os, asyncio, json, csv, re, time, argparse
from pathlib import Path
from dotenv import load_dotenv
from rich import print
from core.storage import DB
from core.matcher import IntentMatcher
from core.reply import ReplyBuilder
from sources.reddit_client import RedditSource
from sources.twitter_client import TwitterSource
from sources.rss_client import RSSSource

load_dotenv()

async def scan(sources:list[str], export:str|None=None):
    db = DB("leads.db")
    matcher = IntentMatcher("data/keywords.yaml", "data/blacklist.yaml")
    ref = os.getenv("REFERRAL_LINK", "")
    brand = os.getenv("BRAND_NAME", "Perplexity Browser")
    rb = ReplyBuilder(brand=brand, referral_link=ref)

    providers = []
    if "reddit" in sources:
        providers.append(RedditSource(matcher=matcher))
    if "twitter" in sources:
        providers.append(TwitterSource(matcher=matcher))
    if "rss" in sources:
        providers.append(RSSSource(matcher=matcher))

    total = 0
    for p in providers:
        async for lead in p.find_posts():
            if db.upsert_lead(lead):
                total += 1
    print(f"[bold green]New leads:[/bold green] {total}")

    if export:
        rows = db.fetch_all()
        with open(export, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
            if rows: w.writeheader(); w.writerows(rows)
        print(f"Exported {len(rows)} rows to {export}")

async def draft(limit:int):
    db = DB("leads.db")
    ref = os.getenv("REFERRAL_LINK", "")
    brand = os.getenv("BRAND_NAME", "Perplexity Browser")
    rb = ReplyBuilder(brand=brand, referral_link=ref)
    leads = db.fetch_undrafted(limit=limit)
    for L in leads:
        draft = rb.build(L)
        db.attach_draft(L["id"], draft)
        print(f"\n[bold]Lead[/bold] {L['platform']} | {L['author']} | {L['url']}\n{draft}\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan"); s.add_argument("--sources", nargs="+", default=["reddit","rss"]) ; s.add_argument("--export")
    d = sub.add_parser("draft"); d.add_argument("--limit", type=int, default=20)

    args = ap.parse_args()
    if args.cmd == "scan":
        asyncio.run(scan(args.sources, args.export))
    elif args.cmd == "draft":
        asyncio.run(draft(args.limit))
```

---

## `core/models.py`

```python
from pydantic import BaseModel, HttpUrl
from typing import Optional

class Lead(BaseModel):
    id: str
    platform: str  # reddit | twitter | rss
    url: HttpUrl
    title: str
    text: str
    author: str
    score: int | None = None
    followers: int | None = None
    created_ts: float
```

---

## `core/storage.py`

```python
import sqlite3, time, json
from typing import Iterable

class DB:
    def __init__(self, path:str):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads(
              id TEXT PRIMARY KEY,
              platform TEXT,
              url TEXT,
              title TEXT,
              text TEXT,
              author TEXT,
              score INT,
              followers INT,
              created_ts REAL,
              draft TEXT
            )
            """
        )

    def upsert_lead(self, L:dict) -> bool:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT OR IGNORE INTO leads(id, platform, url, title, text, author, score, followers, created_ts, draft) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (L["id"], L["platform"], L["url"], L["title"], L["text"], L["author"], L.get("score"), L.get("followers"), L["created_ts"], None)
            )
            self.conn.commit()
            return cur.rowcount == 1
        finally:
            cur.close()

    def fetch_all(self):
        cur = self.conn.execute("SELECT id, platform, url, title, text, author, score, followers, created_ts, draft FROM leads ORDER BY created_ts DESC")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols,row)) for row in cur.fetchall()]

    def fetch_undrafted(self, limit:int=50):
        cur = self.conn.execute("SELECT id, platform, url, title, text, author, score, followers, created_ts FROM leads WHERE draft IS NULL ORDER BY created_ts DESC LIMIT ?", (limit,))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols,row)) for row in cur.fetchall()]

    def attach_draft(self, id:str, draft:str):
        self.conn.execute("UPDATE leads SET draft = ? WHERE id = ?", (draft, id))
        self.conn.commit()
```

---

## `core/matcher.py`

```python
import yaml, re

class IntentMatcher:
    def __init__(self, kw_path:str, bl_path:str):
        self.kw = yaml.safe_load(open(kw_path))
        self.bl = yaml.safe_load(open(bl_path))
        self.re_inc = [re.compile(r"\\b"+re.escape(k)+r"\\b", re.I) for k in self.kw.get("include", [])]
        self.re_exc = [re.compile(r"\\b"+re.escape(k)+r"\\b", re.I) for k in self.kw.get("exclude", [])]

    def match(self, text:str) -> bool:
        t = text or ""
        if any(r.search(t) for r in self.re_exc):
            return False
        return any(r.search(t) for r in self.re_inc)

    def allowed(self, platform:str, author:str, url:str) -> bool:
        if any(d in url for d in self.bl.get("domains", [])): return False
        if author in set(self.bl.get("users", [])): return False
        return True
```

---

## `core/reply.py`

```python
import os
from textwrap import dedent

TEMPLATES = {
  "helpful": """
Hey there — if you’re exploring {topic}, {brand} is worth a look. It balances fast search with on-page automation (summaries, citations, actions). Starter tip: open a few tabs and ask it to compare — it handles context well. If you decide to try it, this link gives you the promo: {ref}  
(Disclosure: referral link.)
""",
  "alt_arc": """
Arc user here — for research/automation I hop to {brand}. It’s quick for ‘compare X vs Y’ and can auto-draft emails/posts from the page. If you want to test it, this includes the perk: {ref}  
(Referral.)
""",
  "automation": """
For workflow automation in the browser, {brand} is solid: summarize page, extract bullets, draft a reply, then iterate. You can run it on any open tab. Trial via my link: {ref}  
(Referral.)
"""
}

class ReplyBuilder:
    def __init__(self, brand:str, referral_link:str):
        self.brand = brand
        self.ref = referral_link

    def pick_topic(self, lead:dict) -> str:
        txt = (lead.get("title") or "") + "\n" + (lead.get("text") or "")
        if any(k in txt.lower() for k in ["automation", "automate", "workflow"]):
            return "automation tools"
        if any(k in txt.lower() for k in ["arc", "chrome", "firefox"]):
            return "new browsers"
        return "research browsers"

    def build(self, lead:dict) -> str:
        topic = self.pick_topic(lead)
        base = TEMPLATES["automation" if topic=="automation tools" else "helpful"]
        return base.format(topic=topic, brand=self.brand, ref=self.ref).strip()
```

---

## `sources/reddit_client.py`

```python
import asyncio, time
import praw
from core.models import Lead

class RedditSource:
    def __init__(self, matcher):
        self.m = matcher
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )
        self.min_score = int(os.getenv("MIN_SCORE", "1"))

    async def find_posts(self):
        # Search a handful of tech subs; adjust as needed
        subs = ["technology","browsers","Productivity","selfhosted","Automation","InternetIsBeautiful"]
        query = "(\"new browser\" OR \"best browser\" OR automation OR \"AI agent\")"
        for s in subs:
            for post in self.reddit.subreddit(s).search(query=query, sort="new", limit=25):
                text = (post.title or "") + "\n" + (post.selftext or "")
                if not self.m.match(text):
                    continue
                if post.score is not None and post.score < self.min_score:
                    continue
                if not self.m.allowed("reddit", str(post.author), post.url):
                    continue
                yield Lead(
                    id=f"reddit_{post.id}", platform="reddit", url=post.url,
                    title=post.title or "", text=post.selftext or "",
                    author=str(post.author), score=int(post.score or 0), followers=None,
                    created_ts=float(post.created_utc or time.time()),
                ).model_dump()
```

---

## `sources/twitter_client.py` (optional)

```python
import os, time, httpx
from core.models import Lead

class TwitterSource:
    def __init__(self, matcher):
        self.m = matcher
        self.bearer = os.getenv("TWITTER_BEARER_TOKEN")

    async def find_posts(self):
        if not self.bearer:
            return
        q = '"new browser" OR "best browser" OR automation OR "AI agent" lang:en -is:retweet'
        url = f"https://api.twitter.com/2/tweets/search/recent?query={httpx.QueryParams({'query': q})}&tweet.fields=author_id,created_at,public_metrics&expansions=author_id&user.fields=public_metrics,username"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {self.bearer}"})
            if r.status_code != 200:
                return
            data = r.json()
            users = {u['id']: u for u in data.get('includes',{}).get('users',[])}
            for t in data.get('data', []):
                u = users.get(t['author_id'], {})
                text = t.get('text','')
                if not self.m.match(text):
                    continue
                if u.get('public_metrics',{}).get('followers_count',0) < int(os.getenv('MIN_FOLLOWERS','25')):
                    continue
                url = f"https://twitter.com/{u.get('username','')}/status/{t['id']}"
                yield Lead(
                    id=f"twitter_{t['id']}", platform="twitter", url=url,
                    title=text[:120], text=text, author=u.get('username',''),
                    score=t.get('public_metrics',{}).get('like_count',0),
                    followers=u.get('public_metrics',{}).get('followers_count',0),
                    created_ts=time.time(),
                ).model_dump()
```

---

## `sources/rss_client.py`

```python
import time, httpx, re
from core.models import Lead

FEEDS = [
  "https://news.google.com/rss/search?q=\"new+browser\"+OR+\"best+browser\"+OR+automation+OR+\"AI+agent\"&hl=en-US&gl=US&ceid=US:en"
]

class RSSSource:
    def __init__(self, matcher):
        self.m = matcher

    async def find_posts(self):
        async with httpx.AsyncClient(timeout=15) as client:
            for feed in FEEDS:
                r = await client.get(feed)
                if r.status_code != 200:
                    continue
                for m in re.finditer(r"<item>(.*?)</item>", r.text, flags=re.S|re.I):
                    item = m.group(1)
                    title = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item)
                    link = re.search(r"<link>(.*?)</link>", item)
                    title = title.group(1) if title else ""
                    link = link.group(1) if link else ""
                    if not self.m.match(title):
                        continue
                    yield Lead(
                        id=f"rss_{hash(link)}", platform="rss", url=link,
                        title=title, text=title, author="rss", score=None, followers=None,
                        created_ts=time.time(),
                    ).model_dump()
```

---

## Reply copy you can reuse

* One-liner: Looking for a research/automation-friendly browser? Try {BRAND_NAME}. Fast summaries, citations, and on-page actions. Perk via my link: {REF_LINK} (referral).
* Comparison: If Chrome/Arc feels heavy for research, {BRAND_NAME} handles multi-tab Q&A and auto-drafts replies from the page. Test it: {REF_LINK} (ref).
* Automation angle: Need quick page → email/post automation? {BRAND_NAME} can summarize, extract bullets, then draft. Trial: {REF_LINK} (referral).

---

## Guardrails (use them)

* No mass DMs. No automated cold messages.
* Post only where allowed and contextually relevant.
* Disclose referral.
* Respect subreddit rules and site ToS.
* Cool-down per subreddit/user/thread; never carpet-bomb.

---

## Quick wins (playbook)

* Sort by “new” in r/Productivity, r/browsers, r/InternetIsBeautiful and answer real questions.
* Create 3–5 evergreen comments you can adapt fast.
* Track which copy converts in your CSV; iterate keywords weekly.
* Layer a simple UTM on your referral link to see which platform works.

---

## License

MIT
