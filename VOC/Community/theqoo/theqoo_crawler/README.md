# Theqoo Crawler

`requests`와 `BeautifulSoup` 기반 더쿠(theqoo) 게시판 크롤러입니다. Selenium은 사용하지 않습니다.

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 실행

```bash
python main.py
python main.py --boards beauty fashion --start 1 --end 30
python main.py --boards beauty --start 1 --end 3 --no-crawl-content
```

CLI 옵션은 `config.py`보다 우선합니다. `--no-crawl-content`를 사용하면 댓글도 수집하지 않습니다.

## config.py

- `BOARDS`: 수집할 게시판 이름 목록
- `START_PAGE`, `END_PAGE`: 수집 페이지 범위
- `CRAWL_CONTENT`: 상세 본문 수집 여부
- `CRAWL_COMMENT`: 댓글 수집 여부
- `SAVE_HTML`: 상세 페이지 원본 HTML 저장 여부
- `REQUEST_DELAY`: 모든 HTTP 요청 사이 대기 시간
- `MAX_RETRY`: 요청 실패 시 재시도 횟수
- `THREAD_WORKERS`: 상세 페이지 병렬 수집 worker 수
- `HEADERS`: 요청 헤더

## 출력

게시글 CSV:

```text
output/theqoo_beauty_1_10.csv
```

댓글 CSV:

```text
output/theqoo_beauty_1_10_comments.csv
```

CSV는 Excel에서 한글이 깨지지 않도록 `utf-8-sig`로 저장합니다.

## 폴더 구조

```text
theqoo_crawler/
  config.py
  crawler.py
  parser.py
  utils.py
  models.py
  main.py
  requirements.txt
  README.md
  output/
  logs/
```

## Resume

동일한 출력 CSV가 이미 있으면 기존 CSV의 `number` 컬럼을 읽고, 이미 저장된 게시글 번호는 건너뜁니다.
