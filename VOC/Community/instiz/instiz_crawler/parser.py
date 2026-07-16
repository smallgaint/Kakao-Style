"""
HTML 파싱 전담 (모든 CSS Selector는 이 파일에서만 관리)
"""

import re
from typing import Optional, List, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

import utils

logger = utils.setup_logger(__name__)


class InstizParser:
    """인스티즈 HTML 파서"""
    
    # parameters: CSS Selector 정의 (사이트 구조 변경 시 여기만 수정)
    SELECTORS = {
        "board": {
            "post_items": ["tr#detour", "tr#greenv", "tr[id]"],
            "title": ["td.listsubject a", ".listsubject a"],
            "comment": ["span.cmt3", "span.cmt"],
            "views": ["td.listhit"],
            "likes": ["td.listrecomendgood"],
            "date": ["td.listdate"],
        },
        "search": {
            "result_links": [
                "td.listsubject a[href]",
                ".listsubject a[href]",
                ".search_item a[href]",
                ".search_list a[href]",
                "a[href]",
                "a[href*='/name_beauty/']",
                "a[href*='/name/']",
                "a[href*='/pt/']",
            ],
            "more_buttons": [
                "a:has-text('더보기')",
                "button:has-text('더보기')",
                "input[value*='더보기']",
                ".more:visible",
                ".more_btn:visible",
                ".btn_more:visible",
                "[class*='more']:visible",
                "[id*='more']:visible",
            ],
        },
        "login": {
            "window": ["#loginwindow"],
            "form": ["form#login", "form[name='login']", "form[action*='login_check.php']"],
            "iframe": ["iframe#ifrm_login", "iframe[name='ifrm_login']"],
            "username": ["#user_id", "input[name='user_id']"],
            "password": ["#password", "input[name='password']"],
            "submit": ["input.login_go", "input[type='submit'][value*='로그인']", "button:has-text('로그인')"],
            "logout": ["a[href*='logout']", "a:has-text('로그아웃')", "a:has-text('로그 아웃')"],
        },
        "detail": {
            "content": ["div.post-content", "div#post_content", "#memo_content", ".memo_content", ".article"],
            "images": ["div.post-content img", "div#post_content img", "#memo_content img", ".memo_content img", ".article img"],
        },
        "comments": {
            "items": ["div.comment-item", "div.reply-item", ".comment_list li", "tr[id^='comment']"],
            "author": ["span.comment-author", ".comment-author", ".nick", ".name"],
            "time": ["span.comment-date", "span.comment-time", ".date", ".time"],
            "content": ["div.comment-text", "p.comment-content", ".comment-content", ".comment_text"],
        },
    }
    
    # 게시판 목록 페이지 Selectors
    POST_ITEM_SELECTOR = SELECTORS["board"]["post_items"][0]  # 게시물 항목 (tr id="detour")
    POST_CATEGORY_SELECTOR = "td.minitext.listnm a"  # 카테고리 링크
    POST_TITLE_SELECTOR = SELECTORS["board"]["title"][0]  # 제목 및 링크
    POST_AUTHOR_SELECTOR = "td.listsigner"  # 작성자 (존재 시)
    POST_COMMENT_SELECTOR = ", ".join(SELECTORS["board"]["comment"])  # 댓글 수
    POST_VIEW_SELECTOR = SELECTORS["board"]["views"][0]  # 조회수
    POST_LIKE_SELECTOR = SELECTORS["board"]["likes"][0]  # 추천수
    POST_DATE_SELECTOR = SELECTORS["board"]["date"][0]  # 작성 날짜
    
    # 게시글 상세 페이지 Selectors
    CONTENT_SELECTOR = ", ".join(SELECTORS["detail"]["content"])
    IMAGES_SELECTOR = ", ".join(SELECTORS["detail"]["images"])
    COMMENT_ITEM_SELECTOR = ", ".join(SELECTORS["comments"]["items"])
    COMMENT_AUTHOR_SELECTOR = ", ".join(SELECTORS["comments"]["author"])
    COMMENT_TIME_SELECTOR = ", ".join(SELECTORS["comments"]["time"])
    COMMENT_TEXT_SELECTOR = ", ".join(SELECTORS["comments"]["content"])
    COMMENT_REPLY_CLASS = "reply-item"

    LOGIN_FORM_SELECTOR = ", ".join(SELECTORS["login"]["form"])
    LOGIN_WINDOW_SELECTOR = ", ".join(SELECTORS["login"]["window"])
    LOGIN_IFRAME_SELECTOR = ", ".join(SELECTORS["login"]["iframe"])
    LOGIN_USERNAME_SELECTOR = ", ".join(SELECTORS["login"]["username"])
    LOGIN_PASSWORD_SELECTOR = ", ".join(SELECTORS["login"]["password"])
    LOGIN_SUBMIT_SELECTOR = ", ".join(SELECTORS["login"]["submit"])
    LOGOUT_SELECTOR = ", ".join(SELECTORS["login"]["logout"])
    
    @staticmethod
    def parse_board_list(
        html: str,
        board: str,
        category: int
    ) -> List[Tuple[int, str, str, str, int, int, int, str, bool]]:
        """게시판 목록 페이지 파싱
        
        Args:
            html: 게시판 목록 HTML
            board: 게시판 이름
            category: 카테고리 번호
            
        Returns:
            (post_id, title, author, url, comment_count, view_count, like_count, date, has_image) 튜플 리스트
        """
        posts = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # parameters: 게시물 항목 추출
            post_items = soup.select(InstizParser.POST_ITEM_SELECTOR)
            
            if not post_items:
                # parameters: 디버그: 실제 HTML 구조 출력
                logger.warning(f"게시물 항목을 찾을 수 없음: {InstizParser.POST_ITEM_SELECTOR}")
                
                # 디버그: 테이블 구조 분석
                tables = soup.find_all('table')
                logger.debug(f"테이블 개수: {len(tables)}")
                
                # 첫 번째 테이블의 행 구조 확인
                if tables:
                    first_table = tables[0]
                    rows = first_table.find_all('tr')
                    logger.debug(f"첫 테이블 행 개수: {len(rows)}")
                    if rows:
                        first_row = rows[0]
                        logger.debug(f"첫 번째 행: id={first_row.get('id')}, class={first_row.get('class')}")
                
                # 대체 Selector 시도: tr#greenv
                logger.debug("대체 1: tr#greenv 시도")
                post_items = soup.select("tr#greenv")
                
                if not post_items:
                    # 대체 Selector 시도: div.listsubject
                    logger.debug("대체 2: div.listsubject 시도")
                    post_items = soup.select("div.listsubject")
                
                if not post_items:
                    # 대체 Selector 시도: table.mboard 내부 tr
                    logger.debug("대체 3: table.mboard tr 시도")
                    post_items = soup.select("table.mboard tr")
                
                if not post_items:
                    logger.debug(f"available tables: {len(soup.select('table'))}, divs: {len(soup.select('div[class*=post]'))}")
                    # 모든 tr[id] 시도
                    logger.debug("대체 4: tr[id] 시도")
                    post_items = soup.select("tr[id]")
                    if post_items:
                        logger.debug(f"tr[id]로 {len(post_items)}개 발견")
                
                if not post_items:
                    return posts
            
            for item in post_items:
                try:
                    # parameters: 제목 및 링크
                    title_elem = item.select_one(InstizParser.POST_TITLE_SELECTOR)
                    if not title_elem:
                        logger.debug("제목 요소 없음")
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    post_url = title_elem.get("href", "")
                    
                    # parameters: 절대 URL 생성
                    if post_url and not post_url.startswith("http"):
                        post_url = f"https://www.instiz.net{post_url}"
                    
                    # parameters: 게시글 ID 추출 (URL에서 추출 또는 td class에서 추출)
                    post_id = 0
                    if post_url:
                        try:
                            # URL 형식: https://www.instiz.net/name_beauty/1668005?category=...
                            post_id = int(post_url.split('/')[4])
                        except (ValueError, IndexError):
                            # 대체: td의 class 속성에서 추출 (r1668005)
                            title_td = item.select_one("td.listsubject")
                            if title_td:
                                td_class = title_td.get("class", [])
                                for cls in td_class:
                                    if cls.startswith("r"):
                                        try:
                                            post_id = int(cls[1:])
                                            break
                                        except ValueError:
                                            pass
                    
                    if post_id == 0:
                        logger.debug(f"게시글 ID를 추출할 수 없음: {post_url}")
                        continue
                    
                    # parameters: 작성자 (파싱 불가능 - Unknown으로 설정)
                    author = "Unknown"
                    
                    # parameters: 댓글 수
                    comment_elem = item.select_one(InstizParser.POST_COMMENT_SELECTOR)
                    comment_count = 0
                    if comment_elem:
                        try:
                            comment_text = comment_elem.get_text(strip=True)
                            comment_count = int(comment_text) if comment_text.isdigit() else 0
                        except (ValueError, AttributeError):
                            pass
                    
                    # parameters: 조회 수 (파싱 불가능 - 0으로 설정)
                    view_count = 0
                    view_elem = item.select_one(InstizParser.POST_VIEW_SELECTOR)
                    if view_elem:
                        try:
                            view_text = view_elem.get_text(strip=True)
                            view_count = int(view_text) if view_text.isdigit() else 0
                        except (ValueError, AttributeError):
                            pass
                    
                    # parameters: 추천 수 (파싱 불가능 - 0으로 설정)
                    like_count = 0
                    like_elem = item.select_one(InstizParser.POST_LIKE_SELECTOR)
                    if like_elem:
                        try:
                            like_text = like_elem.get_text(strip=True)
                            like_count = int(like_text) if like_text.isdigit() else 0
                        except (ValueError, AttributeError):
                            pass
                    
                    # parameters: 작성 일자 (파싱 불가능 - 현재 날짜로 설정)
                    date_elem = item.select_one(InstizParser.POST_DATE_SELECTOR)
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                        created_date = utils.convert_date(date_str)
                    else:
                        # 파싱 불가능하면 현재 날짜 사용
                        from datetime import datetime
                        created_date = datetime.now().strftime("%y.%m.%d")
                    
                    # parameters: 이미지 여부 (제목에 "[사진]" 있는지 확인)
                    has_image = "[사진]" in title or bool(item.select("img"))
                    
                    posts.append((
                        post_id,
                        title,
                        author,
                        post_url,
                        comment_count,
                        view_count,
                        like_count,
                        created_date,
                        has_image
                    ))
                
                except Exception as e:
                    logger.warning(f"게시물 파싱 실패: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"게시판 목록 파싱 실패: {str(e)}")
        
        return posts
    
    @staticmethod
    def parse_search_results(
        html: str,
        board: str,
        category: int,
        keyword: str = ""
    ) -> List[Tuple[int, str, str, str, int, int, int, str, bool]]:
        """검색 결과 HTML에서 게시글 목록을 파싱합니다.

        인스티즈 검색 결과는 로그인 상태/화면 폭/사이트 개편에 따라 table row,
        카드형 링크, 더보기로 추가된 fragment가 섞일 수 있으므로 링크를 기준으로
        보수적으로 수집합니다.
        """
        soup = BeautifulSoup(html, "html.parser")
        posts = InstizParser.parse_board_list(html, board, category) if board else []
        seen_ids = {post[0] for post in posts}

        for selector in InstizParser.SELECTORS["search"]["result_links"]:
            for link_elem in soup.select(selector):
                try:
                    href = link_elem.get("href", "")
                    post_url = urljoin("https://www.instiz.net", href)
                    post_id = InstizParser.extract_post_id(post_url)
                    if not post_id or post_id in seen_ids:
                        continue
                    if board and f"/{board}/" not in urlparse(post_url).path:
                        continue

                    title = InstizParser._clean_title(link_elem.get_text(" ", strip=True))
                    if not title:
                        continue

                    container = link_elem.find_parent(["tr", "li", "article", "div"]) or link_elem
                    container_text = container.get_text(" ", strip=True)
                    comment_count = InstizParser._extract_comment_count(link_elem.get_text(" ", strip=True))
                    view_count = InstizParser._extract_labeled_int(container_text, ["조회"])
                    like_count = InstizParser._extract_labeled_int(container_text, ["추천"])
                    created_date = InstizParser._extract_date(container_text)
                    has_image = bool(container.select("img")) or "[사진]" in title

                    posts.append((
                        post_id,
                        title,
                        "Unknown",
                        post_url,
                        comment_count,
                        view_count,
                        like_count,
                        created_date,
                        has_image,
                    ))
                    seen_ids.add(post_id)
                except Exception as e:
                    logger.warning(f"검색 결과 항목 파싱 실패: {str(e)}")
                    continue

        if keyword and not posts and "검색은 회원만 할 수 있어요" in soup.get_text(" ", strip=True):
            logger.warning("인스티즈 검색 결과가 로그인 전용 화면입니다. 로그인 세션이 없으면 검색 결과가 비어 있을 수 있습니다.")

        return posts

    @staticmethod
    def parse_post_detail(html: str) -> Tuple[Optional[str], int]:
        """게시글 상세 페이지 파싱
        
        Args:
            html: 게시글 상세 HTML
            
        Returns:
            (content_text, image_count) 튜플
        """
        content_text = None
        image_count = 0
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # parameters: 본문 추출
            content_elem = soup.select_one(InstizParser.CONTENT_SELECTOR)
            if content_elem:
                # parameters: 스크립트/스타일 제거
                for tag in content_elem.find_all(["script", "style"]):
                    tag.decompose()
                
                # parameters: 텍스트 추출 (줄바꿈 유지)
                content_text = content_elem.get_text(separator="\n", strip=True)
                
                # parameters: 과도한 연속 줄바꿈 제거 (3개 이상 연속은 1개로)
                while "\n\n\n" in content_text:
                    content_text = content_text.replace("\n\n\n", "\n\n")
            
            # parameters: 이미지 개수
            images = soup.select(InstizParser.IMAGES_SELECTOR)
            image_count = len(images)
        
        except Exception as e:
            logger.warning(f"게시글 상세 파싱 실패: {str(e)}")
        
        return content_text, image_count
    
    @staticmethod
    def parse_comments(html: str) -> List[Tuple[int, str, str, bool, str]]:
        """댓글 파싱
        
        Args:
            html: 게시글 상세 HTML
            
        Returns:
            (comment_number, author, time, is_reply, content) 튜플 리스트
        """
        comments = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # parameters: 댓글 항목
            comment_items = soup.select(InstizParser.COMMENT_ITEM_SELECTOR)
            
            if not comment_items:
                logger.debug("댓글 항목을 찾을 수 없음")
                return comments
            
            comment_number = 1
            
            for item in comment_items:
                try:
                    # parameters: 작성자
                    author_elem = item.select_one(InstizParser.COMMENT_AUTHOR_SELECTOR)
                    author = author_elem.get_text(strip=True) if author_elem else "Unknown"
                    
                    # parameters: 작성 시간
                    time_elem = item.select_one(InstizParser.COMMENT_TIME_SELECTOR)
                    comment_time = time_elem.get_text(strip=True) if time_elem else ""
                    comment_time = utils.convert_date(comment_time)
                    
                    # parameters: 댓글 내용
                    text_elem = item.select_one(InstizParser.COMMENT_TEXT_SELECTOR)
                    content = text_elem.get_text(separator="\n", strip=True) if text_elem else ""
                    
                    # parameters: 대댓글 여부
                    is_reply = InstizParser.COMMENT_REPLY_CLASS in item.get("class", [])
                    
                    comments.append((
                        comment_number,
                        author,
                        comment_time,
                        is_reply,
                        content
                    ))
                    
                    comment_number += 1
                
                except Exception as e:
                    logger.warning(f"댓글 파싱 실패: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"댓글 파싱 실패: {str(e)}")
        
        return comments

    @staticmethod
    def more_button_selectors() -> List[str]:
        """Return Playwright selectors for search-result load-more controls."""
        return InstizParser.SELECTORS["search"]["more_buttons"]

    @staticmethod
    def extract_post_id(url: str) -> int:
        """Extract an Instiz article id from a post URL."""
        match = re.search(r"/([^/?#]+)/(\d+)", urlparse(url).path)
        return int(match.group(2)) if match else 0

    @staticmethod
    def extract_board_name(url: str) -> str:
        """Extract the board path segment from an Instiz post URL."""
        match = re.search(r"/([^/?#]+)/\d+", urlparse(url).path)
        return match.group(1) if match else ""

    @staticmethod
    def _clean_title(text: str) -> str:
        """Remove trailing metric-only fragments from a link title."""
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+\d{2}\.\d{2}.*$", "", text).strip()
        return re.sub(r"\s+\d+$", "", text).strip()

    @staticmethod
    def _extract_comment_count(text: str) -> int:
        """Extract a likely trailing comment count from title text."""
        match = re.search(r"(\d+)\s*$", text.strip())
        return int(match.group(1)) if match else 0

    @staticmethod
    def _extract_labeled_int(text: str, labels: List[str]) -> int:
        """Extract a number following one of the given labels."""
        for label in labels:
            match = re.search(rf"{re.escape(label)}\s*([\d,]+)", text)
            if match:
                return int(match.group(1).replace(",", ""))
        return 0

    @staticmethod
    def _extract_date(text: str) -> str:
        """Extract and normalize a date-like token from surrounding text."""
        match = re.search(r"(\d{2}\.\d{2}(?:\.\d{2})?)", text)
        if match:
            return utils.convert_date(match.group(1))
        from datetime import datetime
        return datetime.now().strftime("%y.%m.%d")
