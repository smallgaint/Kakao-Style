"""Data models used by the crawler and CSV writers."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Post:
    """A board-list row with optional detail-page fields."""

    number: str
    category: str
    title: str
    has_image: bool
    comment_count: int
    date: str
    view_count: int
    link: str
    board: str
    content: str = ""
    image_count: int = 0

    def to_dict(self) -> dict[str, object]:
        """Return a CSV-friendly dictionary."""
        return asdict(self)


@dataclass(slots=True)
class Comment:
    """A comment collected from a detail page."""

    post_number: str
    post_link: str
    board: str
    content: str
    date: str

    def to_dict(self) -> dict[str, str]:
        """Return a CSV-friendly dictionary."""
        return asdict(self)


@dataclass(slots=True)
class CrawlStats:
    """Aggregated crawl statistics."""

    board: str
    pages: int = 0
    posts: int = 0
    comments: int = 0
    errors: int = 0
