"""
전역 설정
"""

# parameters: 크롤링 대상 게시판
BOARDS = [
    {
        "board": "name_beauty",
        "category": 12
    }
]

# parameters: 페이지 범위
START_PAGE = 1
END_PAGE = 2

# parameters: 검색 설정
# CLI에서 --keyword 또는 --keywords를 넘기면 게시판 페이지 순회 대신 검색 결과를 수집합니다.
SEARCH_KEYWORDS = ["지그재그", "직잭", "무신사","에이블리","직쟄", "직젝", "직젴", "zigzag", "29cm", "29CM"]
SEARCH_ALL_BOARDS = True  # True면 board/category를 무시하고 전체 검색 결과만 수집
SEARCH_TYPE = 9  # 1=제목, 5=내용, 9=제목+내용
SEARCH_ENDPOINT = "popup"  # popup=더보기형 검색, board=게시판 list.php 검색
MAX_MORE_CLICKS = 10
MAX_SEARCH_POSTS = 0  # 0이면 제한 없음

# parameters: 로그인 설정
# 비밀번호를 파일에 저장하지 않도록 INSTIZ_ID / INSTIZ_PASSWORD 환경변수 사용을 권장합니다.
LOGIN_ENABLED = True
LOGIN_USERNAME = "smallgaint"
LOGIN_PASSWORD = "2848hohoho"
LOGIN_STORAGE_STATE = "auth/instiz_storage_state.json"
SAVE_LOGIN_STATE = True
MANUAL_LOGIN_WAIT_SECONDS = 0  # 0이면 수동 로그인 대기 없음

# parameters: 수집 옵션
CRAWL_CONTENT = True
CRAWL_COMMENT = True
SAVE_HTML = False
ONLY_NEW_POSTS = False

# parameters: 기본 URL
BASE_URL = "https://www.instiz.net"

# parameters: 요청 설정
REQUEST_DELAY = 1.0
REQUEST_DELAY_RANDOM = True  # ±20%
MAX_RETRY = 3
REQUEST_TIMEOUT = 10  # seconds (legacy, not used with Playwright)

# parameters: 병렬 처리
THREAD_WORKERS = 5

# parameters: HTTP 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# parameters: 브라우저 설정
HEADLESS = True  # headless 모드 (True: 브라우저 표시 없음, False: 브라우저 표시)
BROWSER_TIMEOUT = 30000  # 페이지 로드 타임아웃 (ms)

# parameters: 출력 설정
VERBOSE = True
SHOW_PROGRESS = True

# parameters: 캐시 설정
USE_CACHE = True
CACHE_EXPIRE_HOURS = 24

# parameters: 로깅
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "logs/crawler.log"

# parameters: CSV 인코딩
CSV_ENCODING = "utf-8-sig"  # UTF-8 BOM

# parameters: 필수 컬럼
REQUIRED_POST_COLUMNS = [
    "post_id", "board", "category", "title", "author",
    "comment_count", "view_count", "like_count", "created_date",
    "has_image", "image_count", "post_url"
]

REQUIRED_COMMENT_COLUMNS = [
    "post_id", "post_url", "comment_number", "author",
    "created_time", "is_reply", "content"
]
