# 인스티즈(Instiz) 크롤러

인스티즈 웹사이트의 게시판을 크롤링하여 게시글과 댓글 정보를 수집하는 Python 기반 웹 크롤러입니다.

## 주요 기술

### 왜 Playwright를 사용하나요?

인스티즈(Instiz)는 **JavaScript로 동적 렌더링**을 사용하여 게시글 목록을 로드합니다:

- ❌ `requests` 라이브러리 → 빈 HTML 반환 (0개 게시글)
- ✅ `Playwright` → JavaScript 실행 후 완전한 HTML 반환 (모든 게시글)

따라서 Playwright는 필수이며, 이를 통해 InSTIZ의 JavaScript 렌더링 이후 콘텐츠를 안정적으로 수집합니다.

### 아키텍처

```
Playwright (브라우저 자동화)
    ↓
    페이지 이동 → JavaScript 실행 → 완전한 HTML 획득
    ↓
BeautifulSoup (HTML 파싱)
    ↓
    CSS Selector로 데이터 추출
    ↓
models.py (데이터 저장)
```

**분리 설계**: Playwright는 HTML 수집만, BeautifulSoup는 파싱만 담당 → 체계적이고 유지보수 용이

## 주요 특징

- ✅ **JavaScript 렌더링 지원** - Playwright로 동적 콘텐츠 수집
- ✅ **완전한 게시글 수집** - InSTIZ의 JavaScript 렌더링 후 모든 게시글 획득
- ✅ **자동 재시도** - 타임아웃/연결 오류 시 지수 백오프로 자동 재시도
- ✅ **병렬 처리** - ThreadPoolExecutor로 게시글 본문 병렬 수집
- ✅ **강력한 로깅** - 파일 + 콘솔 동시 출력, 상세한 오류 추적
- ✅ **날짜 변환** - '오늘', '어제', '1시간 전' 등을 YY.MM.DD 형식으로 자동 변환
- ✅ **CLI 옵션** - config.py 외에도 명령줄에서 옵션 설정 가능
- ✅ **캐시 지원** - 동일 URL 재요청 방지
- ✅ **HTML 저장** - 디버깅용 HTML 파일 선택적 저장
- ✅ **Graceful Shutdown** - Ctrl+C로 현재까지 저장 후 종료
- ✅ **Type Hint** - 모든 함수에 타입 힌트 적용
- ✅ **Docstring** - 모든 함수에 상세 설명 포함

## 설치

### 1. 저장소 클론 or 폴더 진입

```bash
cd instiz_crawler
```

### 2. 가상환경 생성 (권장)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. Playwright 브라우저 설치

Playwright가 Chromium 브라우저를 사용하려면 다음을 실행하세요:

```bash
playwright install chromium
```

> ⚠️ **중요**: 이 단계를 완료해야 크롤러가 정상 작동합니다!

## 사용 방법

### 기본 사용 (config.py 기본값 사용)

```bash
python main.py
```

### CLI 옵션으로 실행

```bash
# 특정 게시판 크롤링
python main.py --board name_beauty --category 12 --start 1 --end 20

# 본문만 수집 (댓글 제외)
python main.py --board name_fashion --no-comments

# 큰 범위로 크롤링
python main.py --board name_beauty --start 1 --end 100

# 상세 로그 출력
python main.py --verbose

# HTML 파일 저장
python main.py --save-html

# 캐시 사용
python main.py --use-cache

# 본문/댓글 수집 없음 (게시판 목록만)
python main.py --no-content
```

### 옵션 설명

```
--board BOARD_NAME       크롤링할 게시판 (기본값: config.py의 BOARDS)
--category NUM           카테고리 번호 (기본값: 12)
--start PAGE             시작 페이지 (기본값: config.py의 START_PAGE)
--end PAGE               종료 페이지 (기본값: config.py의 END_PAGE)
--no-content             본문 및 댓글 수집 안 함
--no-comments            댓글만 수집 안 함
--save-html              HTML 파일 저장
--use-cache              캐시 사용
--verbose                상세 로그 출력
--log-level LEVEL        DEBUG/INFO/WARNING/ERROR
```

## config.py 설정

### 브라우저 설정 (새로 추가됨)

```python
# Playwright 브라우저 설정
HEADLESS = True           # 헤드리스 모드 (UI 없이 실행)
BROWSER_TIMEOUT = 30000   # 페이지 로드 타임아웃 (밀리초)
```

- `HEADLESS = True`: 브라우저 UI 표시 안 함 (권장)
- `HEADLESS = False`: 브라우저 창 표시 (디버깅용)
- `BROWSER_TIMEOUT`: 페이지 로드 기다리는 최대 시간

### 크롤링 설정

```python
# 크롤링 대상 게시판
BOARDS = [
    {
        "board": "name_beauty",
        "category": 12
    }
]

# 페이지 범위
START_PAGE = 1
END_PAGE = 20

# 수집 옵션
CRAWL_CONTENT = True      # 본문 수집
CRAWL_COMMENT = True      # 댓글 수집
SAVE_HTML = False         # HTML 저장

# 요청 설정
REQUEST_DELAY = 1.0       # 요청 간격 (초)
REQUEST_DELAY_RANDOM = True  # ±20% 랜덤 지연
MAX_RETRY = 3             # 최대 재시도 횟수
REQUEST_TIMEOUT = 10      # 타임아웃 (초)

# 병렬 처리
THREAD_WORKERS = 5        # 스레드 워커 수
```

## 폴더 구조

```
instiz_crawler/
├── config.py             # 설정 파일
├── models.py             # 데이터 모델
├── parser.py             # HTML 파싱 (CSS Selector 관리)
├── crawler.py            # HTTP 요청 및 크롤링 로직
├── utils.py              # 유틸리티 (날짜, 로깅, 재시도)
├── main.py               # 메인 실행 파일
├── requirements.txt      # 패키지 목록
├── README.md             # 이 파일
├── output/               # 결과 CSV 파일 저장
│   ├── instiz_name_beauty_1_20.csv
│   └── instiz_name_beauty_1_20_comments.csv
├── logs/                 # 로그 파일
│   └── crawler.log
└── html/                 # HTML 파일 (SAVE_HTML=True일 때)
```

## 출력 파일

### 게시글 CSV (instiz_BOARD_START_END.csv)

```csv
post_id,board,category,title,author,comment_count,view_count,like_count,created_date,has_image,image_count,post_url,content
12345,name_beauty,12,"제목","작성자",10,150,5,26.07.13,True,2,"https://www.instiz.net/...",본문내용
```

컬럼 설명:
- `post_id`: 게시글 고유 ID
- `board`: 게시판 이름
- `category`: 카테고리 번호
- `title`: 게시글 제목
- `author`: 작성자
- `comment_count`: 댓글 수
- `view_count`: 조회수
- `like_count`: 추천수
- `created_date`: 작성 날짜 (YY.MM.DD)
- `has_image`: 이미지 첨부 여부
- `image_count`: 이미지 개수
- `post_url`: 게시글 URL
- `content`: 본문 내용 (CRAWL_CONTENT=True일 때만)

### 댓글 CSV (instiz_BOARD_START_END_comments.csv)

```csv
post_id,post_url,comment_number,author,created_time,is_reply,content
12345,"https://www.instiz.net/...",1,"작성자","26.07.13",False,"댓글 내용"
```

컬럼 설명:
- `post_id`: 게시글 ID
- `post_url`: 게시글 URL
- `comment_number`: 댓글 번호
- `author`: 댓글 작성자
- `created_time`: 작성 시간 (YY.MM.DD)
- `is_reply`: 대댓글 여부
- `content`: 댓글 내용

## 로그 파일

`logs/crawler.log`에 다음 정보가 기록됩니다:

```
2024-07-13 14:30:15 [INFO] __main__: 인스티즈 크롤러 시작
2024-07-13 14:30:16 [DEBUG] crawler: 게시판 목록 요청: https://www.instiz.net/name_beauty?page=1&category=12
2024-07-13 14:30:17 [INFO] parser: 게시판 크롤링 완료: 15개 게시글 수집
...
2024-07-13 14:35:42 [INFO] __main__: 크롤링 완료
```

## 실행 예시

### 기본 실행

```bash
python main.py
```

출력:
```
[name_beauty] 페이지: 100%|██████████| 20/20
게시글 본문: 100%|██████████| 152/152
==================================================
크롤링 완료
==================================================
시작 시간: 2024-07-13T14:30:15.123456
종료 시간: 2024-07-13T14:35:42.654321
실행 시간: 5분 27초
--------------------------------------------------
게시판 수: 1
페이지 수: 20
게시글 수: 152
댓글 수: 1240
--------------------------------------------------
오류 수: 2
재시도 횟수: 3
평균 처리 속도: 0.47 게시글/초
==================================================
```

### 대량 크롤링

```bash
python main.py --board name_beauty --start 1 --end 100 --verbose
```

### 게시판만 수집 (본문 제외)

```bash
python main.py --no-content
```

## 개발 구조

### 파일별 책임

| 파일 | 책임 |
|------|------|
| `config.py` | 모든 설정값 중앙화 |
| `models.py` | Post, Comment 데이터 모델 |
| `parser.py` | BeautifulSoup 기반 HTML 파싱 (CSS Selector만 관리) |
| `crawler.py` | HTTP 요청 및 크롤링 로직 |
| `utils.py` | 날짜 변환, 로깅, 재시도, 파일 함수 |
| `main.py` | CLI 처리 및 전체 흐름 제어 |

### CSS Selector 변경

사이트 구조가 변경되면 `parser.py`의 Selector만 수정하면 됩니다:

```python
# parser.py의 상단 부분
class InstizParser:
    POST_ITEM_SELECTOR = "tr[id]"  # 여기만 수정
    POST_TITLE_SELECTOR = "a.subject_link"  # 여기만 수정
    # ... 나머지도 동일
```

## 성능 팁

### 속도 최적화

**Playwright vs 일반 HTTP 비교**:
- Playwright (JavaScript 렌더링): ~1-3초/페이지 (필수 - InSTIZ는 JS 렌더링 필요)
- 일반 HTTP requests: ~0.1-0.5초/페이지 (JS 렌더링 필요한 사이트에는 작동 불가)

**⚡ 성능 최적화 방법**:

1. **스레드 워커 수 조정** (게시글 본문 병렬 수집)
   ```python
   THREAD_WORKERS = 10  # 기본값 5에서 증가
   ```

2. **요청 지연 단축** (서버 부하 주의)
   ```python
   REQUEST_DELAY = 0.5  # 기본값 1.0에서 단축
   ```

3. **페이지 로드 타임아웃 조정**
   ```python
   BROWSER_TIMEOUT = 20000  # 기본값 30000에서 단축 (불안정할 수 있음)
   ```

4. **헤드리스 모드 사용** (권장 - 기본값)
   ```python
   HEADLESS = True  # UI 렌더링 제외로 성능 향상
   ```

5. **캐시 사용**
   ```bash
   python main.py --use-cache
   ```

6. **본문 수집 비활성화** (게시판 목록만 필요한 경우)
   ```bash
   python main.py --no-content
   ```

### 실제 크롤링 시간 예상

- **게시판 목록만**: 50페이지 ≈ 1-2분 (~1초/페이지 × 병렬화)
- **게시판 + 본문**: 50페이지 × 150게시글 ≈ 5-10분 (병렬 처리 적용)

1. **스레드 워커 수 조정**
   ```python
   THREAD_WORKERS = 10  # 기본값 5에서 증가
   ```

2. **요청 지연 단축** (서버 부하 주의)
   ```python
   REQUEST_DELAY = 0.5  # 기본값 1.0에서 단축
   ```

3. **캐시 사용**
   ```python
   USE_CACHE = True
   ```

4. **본문 수집 비활성화** (게시판만 필요한 경우)
   ```bash
   python main.py --no-content
   ```

## 주의사항

- 과도한 요청은 서버에 부담을 줄 수 있습니다
- REQUEST_DELAY를 너무 작게 설정하지 마세요
- User-Agent는 적절하게 설정되어 있습니다
- IP 차단을 방지하기 위해 적절한 지연을 유지하세요

## 라이선스

개인용 학습 목적으로만 사용하세요.

## 문제 해결

### "게시물 항목을 찾을 수 없음" 오류

사이트 구조가 변경되었을 수 있습니다. `parser.py`의 CSS Selector를 확인하고 업데이트하세요.

### 요청 타임아웃

```python
REQUEST_TIMEOUT = 30  # 값을 더 증가시키세요
REQUEST_DELAY = 2.0   # 지연을 증가시키세요
```

### 많은 재시도 발생

서버가 요청을 거부할 수 있습니다:
- REQUEST_DELAY 증가
- 크롤링 시간대 변경
- IP 프록시 사용 고려

### CSV 인코딩 오류

```python
CSV_ENCODING = "utf-8"  # "utf-8-sig" 대신 사용
```

## 역사

- v1.0 (2024-07) - 초기 릴리스

---

**마지막 업데이트**: 2024-07-13
