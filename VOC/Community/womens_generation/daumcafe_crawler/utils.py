"""Shared helpers for dates, CSV, logging, cache, and validation."""

from __future__ import annotations

import csv
import hashlib
import logging
import random
import re
import time
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

from models import Comment, Post


POST_FIELDS = [
    "number",
    "post_id",
    "board",
    "category",
    "title",
    "author",
    "has_image",
    "image_count",
    "comment_count",
    "date",
    "view_count",
    "link",
    "content",
]

COMMENT_FIELDS = ["post_number", "post_link", "comment_number", "author", "date", "content"]


def ensure_directories(*paths: Path) -> None:
    """Create directories if they do not exist."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def setup_logging(log_dir: Path) -> logging.Logger:
    """Configure console and file logging."""
    ensure_directories(log_dir)
    logger = logging.getLogger("daumcafe_crawler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_dir / "crawler.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def clean_text(value: str | None) -> str:
    """Collapse repeated whitespace in text."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_int(value: str | None, default: int = 0) -> int:
    """Parse a permissive integer from text."""
    if not value:
        return default
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else default


def normalize_date(raw: str, today: date | None = None) -> str:
    """Normalize Daum Cafe dates into YY.MM.DD."""
    current = today or date.today()
    text = clean_text(raw)
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{2}", text):
        return text
    if re.fullmatch(r"\d{2}\.\d{2}", text):
        return f"{current.year % 100:02d}.{text}"
    if re.fullmatch(r"\d{1,2}:\d{2}", text):
        return f"{current.year % 100:02d}.{current.month:02d}.{current.day:02d}"
    if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}.*", text):
        return text[2:10]
    if len(text) >= 8 and text[:8].isdigit():
        return f"{text[2:4]}.{text[4:6]}.{text[6:8]}"
    return text


def polite_sleep(base_delay: float, random_rate: float) -> None:
    """Sleep using REQUEST_DELAY plus or minus a configured random rate."""
    jitter = base_delay * random_rate
    time.sleep(max(0.0, base_delay + random.uniform(-jitter, jitter)))


def post_csv_path(output_dir: Path, board: str, start: int, end: int) -> Path:
    """Build the post CSV path."""
    return output_dir / f"daumcafe_{board}_{start}_{end}.csv"


def comment_csv_path(output_dir: Path, board: str, start: int, end: int) -> Path:
    """Build the comment CSV path."""
    return output_dir / f"daumcafe_{board}_{start}_{end}_comments.csv"


def cache_path(cache_dir: Path, url: str) -> Path:
    """Return a stable cache path for a URL."""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.html"


def load_existing_posts(path: Path) -> list[Post]:
    """Load existing posts so reruns preserve old rows."""
    if not path.exists():
        return []
    posts: list[Post] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            number = row.get("number", "").strip()
            if not number:
                continue
            posts.append(
                Post(
                    number=number,
                    post_id=row.get("post_id", ""),
                    board=row.get("board", ""),
                    category=row.get("category", ""),
                    title=row.get("title", ""),
                    author=row.get("author", ""),
                    has_image=str(row.get("has_image", "")).lower() == "true",
                    image_count=parse_int(row.get("image_count", "")),
                    comment_count=parse_int(row.get("comment_count", "")),
                    date=row.get("date", ""),
                    view_count=parse_int(row.get("view_count", "")),
                    link=row.get("link", ""),
                    content=row.get("content", ""),
                )
            )
    return posts


def load_existing_comments(path: Path) -> list[Comment]:
    """Load existing comments so reruns preserve old rows."""
    if not path.exists():
        return []
    comments: list[Comment] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            content = row.get("content", "").strip()
            if content:
                comments.append(
                    Comment(
                        post_number=row.get("post_number", ""),
                        post_link=row.get("post_link", ""),
                        comment_number=row.get("comment_number", ""),
                        author=row.get("author", ""),
                        date=row.get("date", ""),
                        content=content,
                    )
                )
    return comments


def merge_posts(existing: Sequence[Post], incoming: Sequence[Post]) -> list[Post]:
    """Merge posts by post_id or number."""
    merged = {_post_key(post): post for post in existing}
    for post in incoming:
        merged[_post_key(post)] = post
    return sorted(merged.values(), key=lambda item: parse_int(item.number), reverse=True)


def merge_comments(existing: Sequence[Comment], incoming: Sequence[Comment]) -> list[Comment]:
    """Merge comments by stable identity."""
    merged: dict[tuple[str, str, str, str], Comment] = {}
    for comment in [*existing, *incoming]:
        key = (comment.post_number, comment.comment_number, comment.date, comment.content)
        merged[key] = comment
    return list(merged.values())


def validate_posts(posts: Sequence[Post]) -> None:
    """Validate required columns before writing."""
    for idx, post in enumerate(posts, start=1):
        missing = [name for name in ["number", "board", "title", "link"] if not str(getattr(post, name)).strip()]
        if missing:
            raise ValueError(f"Post #{idx} missing required columns: {', '.join(missing)}")


def write_posts(path: Path, posts: Sequence[Post]) -> None:
    """Write post CSV with UTF-8 BOM."""
    validate_posts(posts)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POST_FIELDS)
        writer.writeheader()
        writer.writerows(post.to_dict() for post in posts)


def write_comments(path: Path, comments: Iterable[Comment]) -> None:
    """Write comment CSV with UTF-8 BOM."""
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COMMENT_FIELDS)
        writer.writeheader()
        writer.writerows(comment.to_dict() for comment in comments)


def _post_key(post: Post) -> str:
    """Return a stable key for a post."""
    return post.post_id or post.number
