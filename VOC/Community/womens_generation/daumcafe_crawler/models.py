"""Data models for Daum Cafe crawl results."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Post:
    """A Daum Cafe article row with optional detail fields."""

    number: str
    post_id: str
    board: str
    category: str
    title: str
    author: str
    has_image: bool
    image_count: int
    comment_count: int
    date: str
    view_count: int
    link: str
    content: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a CSV-friendly dictionary."""
        return asdict(self)


@dataclass(slots=True)
class Comment:
    """A Daum Cafe article comment."""

    post_number: str
    post_link: str
    comment_number: str
    author: str
    date: str
    content: str

    def to_dict(self) -> dict[str, str]:
        """Return a CSV-friendly dictionary."""
        return asdict(self)


@dataclass(slots=True)
class CrawlStats:
    """Aggregated crawl statistics for one board."""

    board: str
    pages: int = 0
    posts: int = 0
    comments: int = 0
    errors: int = 0
