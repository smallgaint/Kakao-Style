# Pannate keyword search crawler

Pann 톡톡 전체 검색을 키워드별·최신순으로 순회해, `START_DATE`부터 `END_DATE`까지(양 끝 포함) 작성된 글과 댓글을 수집합니다. 검색 결과가 `START_DATE` 이전으로 내려가면 그 키워드를 종료합니다.

## Run

```powershell
cd VOC\Community\pannate\pannate_crawler
pip install -r requirements.txt
python main.py
python main.py --keywords 지그재그 에이블리 --start-date 2025-07-16 --end-date 2026-07-16
```

`config.py`에서 키워드·고정 날짜 구간·요청 속도·HTML 보관 여부를 변경할 수 있습니다.

## Output

- `data/pann_posts.csv`: 게시글 ID, 검색 키워드, 제목, 댓글 수, 게시판, 작성자, 작성일, 조회수, URL, 본문
- `data/pann_comments.csv`: 게시글 ID/URL, 댓글 작성자, 작성일, 내용

두 파일은 UTF-8 BOM CSV입니다. 기존 CSV가 있으면 게시글 ID와 댓글 ID/작성일/내용을 기준으로 중복을 제거하고 이어서 수집합니다.
