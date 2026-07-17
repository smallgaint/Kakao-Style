"""Runtime configuration for the Daum Cafe crawler."""

from __future__ import annotations

from pathlib import Path

BASE_URL = "https://cafe.daum.net"
CAFE_CODE = "subdued20club"
GRPID = "1IHuH"

SEARCH_KEYWORDS = ["지그재그", "직잭", "무신사", "에이블리", "직잭원", "직잭일", "직잭업", "zigzag", "29cm", "29CM"]
SEARCH_START_DATE = "2025-07-01"  # YYYY-MM-DD, inclusive
SEARCH_END_DATE = "2026-07-16"  # YYYY-MM-DD, inclusive
SEARCH_START_PAGE = 1
SEARCH_LIST_SIZE = 20
CHECKPOINT_SIZE = 50

# A single switch for article bodies and comments. Search-result rows are
# always collected, even when this is False.
CRAWL_DETAILS = False
SAVE_HTML = False

# Daum/Kakao credentials must be supplied through DAUM_ID / DAUM_PASSWORD.
LOGIN_ENABLED = False
LOGIN_STORAGE_STATE = "auth/daum_storage_state.json"
SAVE_LOGIN_STATE = True
MANUAL_LOGIN_WAIT_SECONDS = 0
HEADLESS = False
BROWSER_TIMEOUT = 30_000

REQUEST_DELAY = 1.0
RANDOM_DELAY_RATE = 0.2
MAX_RETRY = 3

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
