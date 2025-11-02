from __future__ import annotations

import argparse
import asyncio
import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from rich import print

from core.matcher import IntentMatcher
from core.reply import ReplyBuilder
from core.storage import DB
from sources.reddit_client import RedditSource
from sources.rss_client import RSSSource
from sources.twitter_client import TwitterSource


load_dotenv()


def get_repo_path() -> Path:
    """Return the project root path."""
    return Path(__file__).resolve().parent


def build_matcher() -> IntentMatcher:
    root = get_repo_path()
    keywords_path = root / "data" / "keywords.yaml"
    blacklist_path = root / "data" / "blacklist.yaml"
    return IntentMatcher(str(keywords_path), str(blacklist_path))


def build_reply_builder() -> ReplyBuilder:
    referral_link = os.getenv("REFERRAL_LINK", "")
    brand_name = os.getenv("BRAND_NAME", "Perplexity Browser")
    return ReplyBuilder(brand=brand_name, referral_link=referral_link)


async def scan(sources: list[str], export: str | None = None) -> None:
    db = DB("leads.db")
    matcher = build_matcher()

    providers = []
    if "reddit" in sources:
        providers.append(RedditSource(matcher=matcher))
    if "twitter" in sources:
        providers.append(TwitterSource(matcher=matcher))
    if "rss" in sources:
        providers.append(RSSSource(matcher=matcher))

    total_new = 0
    for provider in providers:
        async for lead in provider.find_posts():
            if db.upsert_lead(lead):
                total_new += 1
    print(f"[bold green]New leads:[/bold green] {total_new}")

    if export:
        rows = db.fetch_all()
        export_path = Path(export)
        with export_path.open("w", newline="", encoding="utf-8") as fh:
            if rows:
                writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            else:
                fh.write("")
        print(f"Exported {len(rows)} rows to {export_path}")


async def draft(limit: int) -> None:
    db = DB("leads.db")
    reply_builder = build_reply_builder()
    leads = db.fetch_undrafted(limit=limit)
    for lead in leads:
        draft_text = reply_builder.build(lead)
        db.attach_draft(lead["id"], draft_text)
        print(
            f"\n[bold]Lead[/bold] {lead['platform']} | {lead['author']} | {lead['url']}\n"
            f"{draft_text}\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Referral Finder Bot CLI")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan platforms for new leads")
    scan_parser.add_argument(
        "--sources",
        nargs="+",
        default=["reddit", "rss"],
        choices=["reddit", "twitter", "rss"],
        help="Platforms to scan",
    )
    scan_parser.add_argument("--export", help="Optional path to export all leads as CSV")

    draft_parser = subparsers.add_parser("draft", help="Draft replies for stored leads")
    draft_parser.add_argument("--limit", type=int, default=20, help="Maximum drafts to generate")

    args = parser.parse_args()

    if args.cmd == "scan":
        asyncio.run(scan(args.sources, args.export))
    elif args.cmd == "draft":
        asyncio.run(draft(args.limit))


if __name__ == "__main__":
    main()
