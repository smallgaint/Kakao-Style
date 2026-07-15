"""Shared helpers for logging, dates, paths, CSV, and resume support."""

from __future__ import annotations

import csv
import logging
import re
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

from models import Comment, Post


POST_FIELDS = [
    "number",
    "category",
    "title",
    "has_image",
    "comment_count",
    "date",
    "view_count",
    "link",
    "board",
    "content",
    "image_count",
]

COMMENT_FIELDS = ["post_number", "post_link", "board", "content", "date"]


def ensure_directories(*paths: Path) -> None:
    """Create required directories if they do not exist."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def setup_logging(log_dir: Path) -> logging.Logger:
    """Configure file and console logging."""
    ensure_directories(log_dir)
    logger = logging.getLogger("theqoo_crawler")
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
    """Collapse repeated whitespace while preserving meaningful text."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_int(value: str | None, default: int = 0) -> int:
    """Parse an integer from text that may contain commas or labels."""
    if not value:
        return default
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else default


def normalize_date(raw: str, today: date | None = None) -> str:
    """Normalize Theqoo date text into YY.MM.DD."""
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
    return text


def post_csv_path(output_dir: Path, board: str, start: int, end: int) -> Path:
    """Build the post CSV path for a board and page range."""
    return output_dir / f"theqoo_{board}_{start}_{end}.csv"


def comment_csv_path(output_dir: Path, board: str, start: int, end: int) -> Path:
    """Build the comment CSV path for a board and page range."""
    return output_dir / f"theqoo_{board}_{start}_{end}_comments.csv"


def load_existing_numbers(path: Path) -> set[str]:
    """Read already collected post numbers for resume mode."""
    return {post.number for post in load_existing_posts(path)}


def load_existing_posts(path: Path) -> list[Post]:
    """Read existing post rows so resume mode can preserve old data."""
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
                    category=row.get("category", ""),
                    title=row.get("title", ""),
                    has_image=str(row.get("has_image", "")).lower() == "true",
                    comment_count=parse_int(row.get("comment_count", "")),
                    date=row.get("date", ""),
                    view_count=parse_int(row.get("view_count", "")),
                    link=row.get("link", ""),
                    board=row.get("board", ""),
                    content=row.get("content", ""),
                    image_count=parse_int(row.get("image_count", "")),
                )
            )
    return posts


def load_existing_comments(path: Path) -> list[Comment]:
    """Read existing comments so they are not lost on rerun."""
    if not path.exists():
        return []
    comments: list[Comment] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            content = row.get("content", "").strip()
            if not content:
                continue
            comments.append(
                Comment(
                    post_number=row.get("post_number", ""),
                    post_link=row.get("post_link", ""),
                    board=row.get("board", ""),
                    content=content,
                    date=row.get("date", ""),
                )
            )
    return comments


def merge_posts(existing: Sequence[Post], incoming: Sequence[Post]) -> list[Post]:
    """Merge posts by number, keeping incoming rows for newly collected posts."""
    merged = {post.number: post for post in existing}
    for post in incoming:
        merged[post.number] = post
    return sorted(merged.values(), key=_post_sort_key, reverse=True)


def merge_comments(existing: Sequence[Comment], incoming: Sequence[Comment]) -> list[Comment]:
    """Merge comments using stable content/date/link identity."""
    merged: dict[tuple[str, str, str, str], Comment] = {}
    for comment in [*existing, *incoming]:
        key = (comment.post_number, comment.post_link, comment.date, comment.content)
        merged[key] = comment
    return list(merged.values())


def validate_posts(posts: Sequence[Post]) -> None:
    """Validate required post fields before writing CSV."""
    required = ["number", "title", "link", "board"]
    for index, post in enumerate(posts, start=1):
        missing = [field for field in required if not str(getattr(post, field, "")).strip()]
        if missing:
            raise ValueError(f"Post #{index} missing required columns: {', '.join(missing)}")


def write_posts(path: Path, posts: Sequence[Post]) -> None:
    """Write post rows to a UTF-8 BOM CSV."""
    validate_posts(posts)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POST_FIELDS)
        writer.writeheader()
        writer.writerows(post.to_dict() for post in posts)


def write_comments(path: Path, comments: Iterable[Comment]) -> None:
    """Write comment rows to a UTF-8 BOM CSV."""
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COMMENT_FIELDS)
        writer.writeheader()
        writer.writerows(comment.to_dict() for comment in comments)


def _post_sort_key(post: Post) -> int:
    """Sort numeric post numbers first and non-numeric values last."""
    return int(post.number) if post.number.isdigit() else -1
