"""
데이터 모델 정의
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime


@dataclass
class Post:
    """게시글 데이터 모델"""
    
    post_id: int
    board: str
    category: int
    title: str
    author: str
    comment_count: int
    view_count: int
    like_count: int
    created_date: str
    has_image: bool
    image_count: int
    post_url: str
    content: Optional[str] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return asdict(self)


@dataclass
class Comment:
    """댓글 데이터 모델"""
    
    post_id: int
    post_url: str
    comment_number: int
    author: str
    created_time: str
    is_reply: bool
    content: str
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return asdict(self)


@dataclass
class CrawlLog:
    """크롤링 로그"""
    
    start_time: datetime
    end_time: Optional[datetime] = None
    boards: int = 0
    pages: int = 0
    posts: int = 0
    comments: int = 0
    errors: list = field(default_factory=list)
    retries: int = 0
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "boards": self.boards,
            "pages": self.pages,
            "posts": self.posts,
            "comments": self.comments,
            "errors": self.errors,
            "retries": self.retries,
        }
