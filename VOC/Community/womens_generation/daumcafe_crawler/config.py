"""Runtime configuration for the Daum Cafe crawler."""

from __future__ import annotations

from pathlib import Path

BASE_URL = "https://cafe.daum.net"
CAFE_CODE = "subdued20club"
GRPID = "1IHuH"

BOARDS = ["ReHf"]
START_PAGE = 1
END_PAGE = 20

CRAWL_CONTENT = True
CRAWL_COMMENT = True
ONLY_NEW_POSTS = True
SAVE_HTML = False
USE_CACHE = True

REQUEST_DELAY = 1.0
RANDOM_DELAY_RATE = 0.2
TIMEOUT = 15
MAX_RETRY = 3
THREAD_WORKERS = 5

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
LOG_DIR = PROJECT_DIR / "logs"
HTML_DIR = PROJECT_DIR / "html"
CACHE_DIR = PROJECT_DIR / ".cache"

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
