"""Configuration for the Pann newest-first keyword search crawler."""

from datetime import date
from pathlib import Path

BASE_URL = "https://pann.nate.com"
SEARCH_URL = f"{BASE_URL}/search/talk"
COMMENT_LOAD_URL = f"{BASE_URL}/talk/reply/load"

# Searches are run in this exact order. Add or remove terms as needed.
KEYWORDS = ["지그재그", "직잭", "직젝", "직쟄", "직젴", "무신사", "에이블리", "29cm", "29CM", "zigzag"]
SORT = "DD"  # newest first

# Both endpoints are inclusive. Update this fixed window before each collection.
START_DATE = date(2025, 7, 16)
END_DATE = date(2026, 7, 16)

CRAWL_CONTENT = True
CRAWL_COMMENT = True
SAVE_HTML = False
ENABLE_RESUME = True

REQUEST_DELAY = 1.0
REQUEST_DELAY_RANDOM = 0.3
MAX_RETRY = 3
TIMEOUT = 30
AUTO_SAVE_EVERY = 10
MAX_PAGES_PER_KEYWORD = 10_000

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
HTML_DIR = DATA_DIR / "html"
LOG_DIR = PROJECT_DIR / "logs"
POST_OUTPUT = DATA_DIR / "pann_posts.csv"
COMMENT_OUTPUT = DATA_DIR / "pann_comments.csv"
LOG_FILE = LOG_DIR / "crawler.log"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": BASE_URL,
}
