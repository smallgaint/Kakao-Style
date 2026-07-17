# Daum Cafe Search Crawler

여성시대 카페 전체 게시판에서 키워드 검색 결과를 기간별로 수집합니다. 검색 결과의 미리보기는 항상 저장하며, `CRAWL_DETAILS=True`일 때만 로그인 세션으로 상세 본문과 댓글을 수집합니다.

## Setup

```powershell
pip install -r requirements.txt
python -m playwright install chromium
$env:DAUM_ID = "your-id"
$env:DAUM_PASSWORD = "your-password"
```

로그인 세션은 `auth/daum_storage_state.json`에 저장되어 다음 실행에 재사용됩니다.

## Run

`config.py`에서 `SEARCH_KEYWORDS`, `SEARCH_START_DATE`, `SEARCH_END_DATE`, `CRAWL_DETAILS`를 설정한 뒤 실행합니다.

```powershell
python main.py
python main.py --keywords 지그재그 에이블리 --start-date 2026-07-01 --end-date 2026-07-16
python main.py --crawl-details
python main.py --headed
```

결과는 `output/daumcafe_search_YYYYMMDD_YYYYMMDD.csv` 및 상세 수집 시 댓글 CSV에 저장됩니다. 대상 게시글 50건마다 중간 저장합니다.
