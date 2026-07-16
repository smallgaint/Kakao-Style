"""CSV persistence, deduplication, and logging helpers."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from models import Comment, Post

POST_FIELDS = ["post_id", "matched_keywords", "title", "comment_count", "board", "author", "created_at", "view_count", "url", "content"]
COMMENT_FIELDS = ["post_id", "post_url", "author", "created_at", "content"]


def ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def setup_logging(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pannate_crawler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def load_posts(path: Path) -> list[Post]:
    if not path.exists():
        return []
    posts: list[Post] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            try:
                posts.append(Post(
                    post_id=row["post_id"], matched_keywords=row.get("matched_keywords", ""),
                    title=row["title"], comment_count=int(row.get("comment_count") or 0),
                    board=row.get("board", ""), author=row.get("author", ""),
                    created_at=datetime.fromisoformat(row["created_at"]), view_count=int(row.get("view_count") or 0),
                    url=row["url"], content=row.get("content", ""),
                ))
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Invalid post CSV row in {path}: {row}") from exc
    return posts


def load_comments(path: Path) -> list[Comment]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as file:
        return [Comment(row["post_id"], row["post_url"], row.get("author", ""), row.get("created_at", ""), row["content"]) for row in csv.DictReader(file) if row.get("content")]


def merge_posts(existing: Sequence[Post], incoming: Sequence[Post]) -> list[Post]:
    merged = {post.post_id: post for post in existing}
    for post in incoming:
        merged[post.post_id] = post
    return sorted(merged.values(), key=lambda post: (post.created_at, post.post_id), reverse=True)


def merge_comments(existing: Sequence[Comment], incoming: Sequence[Comment]) -> list[Comment]:
    merged = {(comment.post_id, comment.created_at, comment.content): comment for comment in [*existing, *incoming]}
    return list(merged.values())


def write_posts(path: Path, posts: Iterable[Post]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POST_FIELDS)
        writer.writeheader()
        writer.writerows(post.to_dict() for post in posts)


def write_comments(path: Path, comments: Iterable[Comment]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COMMENT_FIELDS)
        writer.writeheader()
        writer.writerows(comment.to_dict() for comment in comments)
