"""Runtime configuration for the Theqoo crawler."""

from __future__ import annotations

from pathlib import Path

BASE_URL = "https://theqoo.net"

BOARDS = ["beauty"]
START_PAGE = 1
END_PAGE = 1

CRAWL_CONTENT = True
CRAWL_COMMENT = True
SAVE_HTML = True

# 제목에 포함될 키워드 목록 (빈 리스트일 경우 전체 수집)
KEYWORDS: list[str] = []

REQUEST_DELAY = 1.0
TIMEOUT = 15
MAX_RETRY = 3
THREAD_WORKERS = 5

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
LOG_DIR = PROJECT_DIR / "logs"
HTML_DIR = PROJECT_DIR / "html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
    "Connection": "keep-alive",
}
