"""CSV data models for Pann posts and comments."""

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Post:
    post_id: str
    matched_keywords: str
    title: str
    comment_count: int
    board: str
    author: str
    created_at: datetime
    view_count: int
    url: str
    content: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["created_at"] = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return data


@dataclass(frozen=True, slots=True)
class Comment:
    post_id: str
    post_url: str
    author: str
    created_at: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class CrawlStats:
    search_pages: int = 0
    posts: int = 0
    comments: int = 0
    errors: int = 0
