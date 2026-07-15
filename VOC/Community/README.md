# 커뮤니티 크롤러

다양한 온라인 커뮤니티의 게시글과 댓글 데이터를 수집하는 Python 기반 웹 크롤러 프로젝트입니다.

## 지원하는 커뮤니티

- **인스티즈 (Instiz)**
- **네이트 판 (Nate Pann)**

## 프로젝트 구조

```
Community/
├── instiz/
│   └── instiz_crawler/     # 인스티즈 크롤러
│       ├── main.py
│       ├── crawler.py
│       ├── parser.py
│       └── ...
├── pannate/
│   ├── pann_parser.py      # 네이트 판 파서
│   └── parser_factory.py   # URL에 따라 적절한 파서를 선택하는 팩토리
└── README.md               # 현재 파일
```

- 각 커뮤니티별 크롤러는 해당 폴더(`instiz`, `pannate`) 내에서 독립적으로 관리됩니다.
- `parser_factory.py`를 통해 URL을 입력하면 해당 사이트에 맞는 파서(`InstizParser`, `PannParser`)를 동적으로 선택하여 사용할 수 있습니다.

---

## 1. 인스티즈 (Instiz) 크롤러

인스티즈 웹사이트의 게시판을 크롤링하여 게시글과 댓글 정보를 수집합니다.

### 1.1. 주요 기술

#### 왜 Playwright를 사용하나요?

인스티즈는 **JavaScript로 동적 렌더링**을 사용하여 게시글 목록을 로드하므로, `requests`와 같은 정적 라이브러리로는 완전한 데이터를 수집할 수 없습니다. Playwright는 JavaScript 실행 후의 최종 HTML을 가져오므로 안정적인 데이터 수집에 필수적입니다.

```
Playwright (브라우저 자동화)
    ↓
페이지 이동 → JavaScript 실행 → 완전한 HTML 획득
    ↓
BeautifulSoup (HTML 파싱)
    ↓
    CSS Selector로 데이터 추출
    ↓
CSV 파일 저장
```

### 1.2. 주요 특징

- ✅ **동적 콘텐츠 수집**: Playwright로 JavaScript 렌더링 완벽 지원
- ✅ **병렬 처리**: `ThreadPoolExecutor`로 여러 게시글 본문을 동시에 수집하여 속도 향상
- ✅ **자동 재시도 및 로깅**: 네트워크 오류 발생 시 자동 재시도 및 모든 과정을 로그 파일로 기록
- ✅ **유연한 CLI**: `config.py` 설정 외에, 명령줄 옵션으로 크롤링 대상과 방식을 지정

### 1.3. 설치

1.  **`instiz_crawler` 폴더로 이동**
    ```bash
    cd instiz/instiz_crawler
    ```

2.  **가상환경 생성 및 활성화 (권장)**
    ```bash
    # 가상환경 생성
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **패키지 설치**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Playwright 브라우저 설치**
    ```bash
    playwright install chromium
    ```
    > ⚠️ **중요**: 이 단계를 완료해야 크롤러가 정상 작동합니다!

### 1.4. 사용 방법

`instiz/instiz_crawler` 디렉토리 내에서 아래 명령어를 실행하세요.

#### 기본 사용 (`config.py` 설정값 사용)

```bash
python main.py
```

#### CLI 옵션으로 실행

```bash
# 특정 게시판 1~20 페이지 크롤링
python main.py --board name_beauty --category 12 --start 1 --end 20

# 본문 수집 없이 목록만 크롤링
python main.py --board name_fashion --no-content

# 상세 로그 출력
python main.py --verbose
```

#### CLI 옵션 상세

```
--board BOARD_NAME       크롤링할 게시판 (예: name_beauty)
--category NUM           카테고리 번호 (기본값: 12)
--start PAGE             시작 페이지
--end PAGE               종료 페이지
--no-content             게시글 본문 및 댓글 수집 안 함
--no-comments            댓글만 수집 안 함
--save-html              디버깅용 HTML 파일 저장
--use-cache              캐시 사용 (동일 URL 재요청 방지)
--verbose                상세 로그(DEBUG) 출력
```

### 1.5. 출력 파일

-   **게시글**: `output/instiz_{게시판이름}_{시작페이지}_{종료페이지}.csv`
-   **댓글**: `output/instiz_{게시판이름}_{시작페이지}_{종료페이지}_comments.csv`

---

## 2. 네이트 판 (Nate Pann) 파서

네이트 판의 HTML을 파싱하여 게시글 목록, 상세 내용, 댓글 데이터를 추출합니다.

### 2.1. 주요 기술

#### 왜 Playwright가 필요 없나요?

네이트 판은 게시글과 댓글 데이터가 HTML에 정적으로 포함되어 있습니다. 따라서 `requests` 라이브러리로 HTML을 가져온 후 `BeautifulSoup`으로 바로 파싱할 수 있습니다.

### 2.2. 주요 특징

- ✅ **정적 파싱**: `requests`와 `BeautifulSoup`만으로 데이터 추출 가능
- ✅ **3단계 파싱**: 게시판 목록, 게시글 상세, 댓글 정보를 각각 파싱하는 함수 제공
- ✅ **데이터 정제**: 본문 내용에서 광고 등 불필요한 요소를 자동으로 제거

### 2.3. 사용 방법

`PannParser` 클래스는 외부에서 HTML 문자열을 주입받아 파싱하는 역할을 합니다. `instiz_crawler`와 같이 직접 실행하는 `main.py`는 없으며, 다른 스크립트에서 `PannParser`를 임포트하여 사용해야 합니다.

```python
import requests
from pannate.pann_parser import PannParser

# 1. 네이트 판 게시판 HTML 가져오기
url = "https://pann.nate.com/talk/c20031"
response = requests.get(url)
html_content = response.text

# 2. 게시판 목록 파싱
posts = PannParser.parse_board_list(html_content, "자유톡")

# 3. 첫 번째 게시글의 상세 내용 및 댓글 파싱
if posts:
    post_url = posts[0]['url']
    post_response = requests.get(post_url)
    post_html = post_response.text

    details = PannParser.parse_post_detail(post_html)
    comments = PannParser.parse_comments(post_html)

    print("게시글 상세:", details)
    print("댓글:", comments)
```
