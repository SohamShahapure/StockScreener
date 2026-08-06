"""
Wraps PRAW (Reddit's official Python API wrapper). Needs a free "script"
app - see the Phase 7 integration README for the ~3-minute setup at
https://www.reddit.com/prefs/apps.

Searches across a small set of investing-focused subreddits (configurable
via REDDIT_SUBREDDITS) for posts mentioning the company, most recent first.
"""
import praw
from prawcore.exceptions import PrawcoreException

from app.core.config import settings


class RedditFetchError(Exception):
    """Raised for missing credentials, Reddit API errors, or anything else
    that stops us getting posts back. The router turns this into a clean
    502 rather than a raw traceback."""


def _get_client() -> praw.Reddit:
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        raise RedditFetchError(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set. Create a free "
            "'script' app at https://www.reddit.com/prefs/apps and add the keys to .env"
        )
    reddit = praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )
    reddit.read_only = True
    return reddit


def fetch_reddit_posts(query: str, limit: int = 10) -> list[dict]:
    try:
        reddit = _get_client()
    except RedditFetchError:
        raise

    subreddits = [s.strip() for s in settings.REDDIT_SUBREDDITS.split(",") if s.strip()]
    multireddit = "+".join(subreddits) if subreddits else "stocks"

    try:
        submissions = reddit.subreddit(multireddit).search(query, sort="new", time_filter="week", limit=limit)
        posts = []
        for s in submissions:
            posts.append(
                {
                    "author": str(s.author) if s.author else "[deleted]",
                    "content": s.title,
                    "url": f"https://reddit.com{s.permalink}",
                    "score": s.score,
                    "posted_at": _epoch_to_iso(s.created_utc),
                }
            )
        return posts
    except PrawcoreException as e:
        raise RedditFetchError(f"Reddit API error: {e}") from e
    except Exception as e:
        raise RedditFetchError(f"Unexpected error fetching Reddit posts: {e}") from e


def _epoch_to_iso(epoch_seconds: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()
