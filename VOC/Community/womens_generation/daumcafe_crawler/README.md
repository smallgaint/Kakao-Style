# Daum Cafe Crawler

`requests`와 `BeautifulSoup` 기반 Daum Cafe 크롤러입니다. Selenium은 사용하지 않습니다.

## 설치

```powershell
pip install -r requirements.txt
```

## 실행

```powershell
python main.py
python main.py --boards ReHf ReHw --start 1 --end 30
python main.py --boards ReHf --start 1 --end 1 --no-crawl-content
python main.py --boards ReHf --start 1 --end 1 --all-posts
```

CLI 옵션은 `config.py`보다 우선합니다.

## 구조 변경 대응

모든 CSS selector는 `parser.py`의 `SELECTORS` dictionary에서만 관리합니다.

Daum Cafe의 iframe 구조가 바뀌어도 `extract_iframe_src()`가 `iframe#down`, `iframe[name=down]`, 카페 title iframe 후보를 순서대로 찾아 실제 iframe URL을 구성합니다. selector나 iframe 후보가 바뀌면 `parser.py`만 수정하면 됩니다.

## 출력

게시글:

```text
output/daumcafe_ReHf_1_20.csv
```

댓글:

```text
output/daumcafe_ReHf_1_20_comments.csv
```

CSV는 `utf-8-sig`로 저장됩니다.

## 주요 옵션

- `BOARDS`: 게시판 ID 목록
- `START_PAGE`, `END_PAGE`: 페이지 범위
- `CRAWL_CONTENT`: 본문 수집 여부
- `CRAWL_COMMENT`: 댓글 수집 여부
- `ONLY_NEW_POSTS`: 기존 CSV에 없는 신규 게시글만 상세 수집
- `SAVE_HTML`: 원본 HTML 저장
- `USE_CACHE`: 동일 URL HTML 캐시
- `REQUEST_DELAY`, `RANDOM_DELAY_RATE`: 요청 간격과 랜덤 지연
- `THREAD_WORKERS`: 상세 수집 병렬 worker 수
