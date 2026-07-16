"""
Playwright 기반 웹 크롤링 로직 전담
"""

import time
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional, List, Set
from pathlib import Path
from datetime import datetime
import logging
from urllib.parse import urlencode

import config
import utils
from models import Post, Comment, CrawlLog
from parser import InstizParser

logger = utils.setup_logger(__name__)


class InstizCrawler:
    """Playwright 기반 인스티즈 크롤러"""
    
    def __init__(self):
        """크롤러 초기화"""
        # parameters: Playwright 초기화 (나중에 시작)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # parameters: 캐시
        self.url_cache: dict = {}
        self.processed_posts: Set[object] = set()
        
        # parameters: 통계
        self.crawl_log = CrawlLog(start_time=datetime.now())
    
    def start_browser(self) -> None:
        """브라우저 시작
        
        프로그램 시작 시 한 번만 호출
        """
        logger.info("브라우저 시작 중...")
        
        try:
            self.playwright = sync_playwright().start()
            
            # parameters: Chromium 실행
            self.browser = self.playwright.chromium.launch(
                headless=config.HEADLESS
            )
            
            # parameters: Context 생성 (단일 스레드용)
            context_options = {
                "user_agent": config.HEADERS.get("User-Agent", "")
            }
            storage_state = self._resolve_storage_path()
            if storage_state and storage_state.exists():
                context_options["storage_state"] = str(storage_state)
                logger.info(f"저장된 로그인 세션 사용: {storage_state}")

            self.context = self.browser.new_context(**context_options)
            
            logger.info("브라우저 시작 완료")
        
        except Exception as e:
            logger.error(f"브라우저 시작 실패: {str(e)}")
            raise
    
    def close_browser(self) -> None:
        """브라우저 종료
        
        프로그램 종료 시 반드시 호출
        """
        logger.info("브라우저 종료 중...")
        
        try:
            # parameters: Context 종료
            if self.context:
                self.context.close()
            
            # parameters: 브라우저 종료
            if self.browser:
                self.browser.close()
            
            # parameters: Playwright 종료
            if self.playwright:
                self.playwright.stop()
            
            logger.info("브라우저 종료 완료")
        
        except Exception as e:
            logger.error(f"브라우저 종료 중 오류: {str(e)}")

    def login(self, username: str = "", password: str = "") -> bool:
        """인스티즈 로그인 처리.

        저장된 storage_state가 있으면 먼저 재사용하고, 필요할 때만 입력받은 계정으로 로그인합니다.
        """
        if not self.context:
            raise RuntimeError("브라우저가 시작되지 않았습니다. start_browser()를 먼저 호출하세요.")

        page = None
        try:
            page = self.context.new_page()
            self._goto_login_page(page)

            if self._is_logged_in(page) or self._has_search_access(page):
                logger.info("이미 로그인된 세션입니다")
                self._save_login_state()
                return True

            if username and password:
                self._goto_login_page(page)
                if self._is_logged_in(page) or self._has_search_access(page):
                    logger.info("이미 로그인된 세션입니다")
                    self._save_login_state()
                    return True
                self._goto_login_page(page)

                logger.info(f"로그인 시도: {self._mask_username(username)}")
                self._submit_login_form(page, username, password)
                self._wait_for_login_response(page)
                response_message = self._extract_login_response_message(page)
                self._reload_login_page(page)

                if self._is_logged_in(page) or self._has_search_access(page):
                    logger.info("로그인 성공")
                    self._save_login_state()
                    return True

                if response_message:
                    logger.warning(f"로그인 응답: {response_message}")
                logger.warning("자동 로그인 확인 실패")
            else:
                logger.warning("로그인 계정 정보가 없습니다. INSTIZ_ID / INSTIZ_PASSWORD 환경변수 또는 config.py 값을 확인하세요")

            wait_seconds = getattr(config, "MANUAL_LOGIN_WAIT_SECONDS", 0)
            if wait_seconds:
                logger.info(f"수동 로그인 대기: {wait_seconds}초")
                self._goto_login_page(page)
                page.wait_for_timeout(wait_seconds * 1000)
                self._reload_login_page(page)
                if self._is_logged_in(page) or self._has_search_access(page):
                    logger.info("수동 로그인 확인 완료")
                    self._save_login_state()
                    return True

            logger.error("로그인 실패: 아이디/비밀번호를 확인하거나 수동 로그인 대기를 사용하세요")
            return False
        except Exception as e:
            logger.error(f"로그인 처리 중 오류: {str(e)}")
            self.crawl_log.errors.append(f"Login Error: {str(e)}")
            return False
        finally:
            if page:
                try:
                    page.close()
                except Exception as e:
                    logger.warning(f"로그인 페이지 종료 실패: {str(e)}")

    def _goto_login_page(self, page: Page) -> None:
        """로그인 확인용 페이지로 이동."""
        page.goto(config.BASE_URL, wait_until="domcontentloaded", timeout=config.BROWSER_TIMEOUT)
        self._wait_for_login_ready(page)

    def _reload_login_page(self, page: Page) -> None:
        """로그인 상태 확인을 위해 현재 페이지를 새로고침."""
        page.reload(wait_until="domcontentloaded", timeout=config.BROWSER_TIMEOUT)
        self._wait_for_login_ready(page)

    def _wait_for_login_ready(self, page: Page) -> None:
        """광고/외부 요청 때문에 networkidle이 오지 않아도 로그인 확인은 계속 진행."""
        try:
            page.wait_for_selector(
                f"{InstizParser.LOGIN_FORM_SELECTOR}, {InstizParser.LOGOUT_SELECTOR}, body",
                timeout=5000
            )
        except Exception:
            logger.debug("로그인 페이지 준비 대기 timeout, 현재 DOM으로 계속 진행")

        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            logger.debug("networkidle 대기 timeout, 현재 DOM으로 계속 진행")

    def _submit_login_form(self, page: Page, username: str, password: str) -> None:
        """로그인 폼 값 주입 및 제출."""
        try:
            page.locator(InstizParser.LOGIN_WINDOW_SELECTOR).first.evaluate(
                "element => element.style.display = 'block'",
                timeout=3000
            )
        except Exception:
            pass

        try:
            page.locator(InstizParser.LOGIN_USERNAME_SELECTOR).first.fill(username, timeout=3000)
            page.locator(InstizParser.LOGIN_PASSWORD_SELECTOR).first.fill(password, timeout=3000)
            page.locator(InstizParser.LOGIN_SUBMIT_SELECTOR).first.click(timeout=3000)
            return
        except Exception:
            logger.debug("일반 폼 입력 실패, DOM submit 방식으로 재시도")

        page.evaluate(
            """({ username, password, formSelector, usernameSelector, passwordSelector }) => {
                const form = document.querySelector(formSelector);
                const userInput = document.querySelector(usernameSelector);
                const passwordInput = document.querySelector(passwordSelector);
                if (!form || !userInput || !passwordInput) {
                    throw new Error("login form not found");
                }
                userInput.value = username;
                passwordInput.value = password;
                userInput.dispatchEvent(new Event("input", { bubbles: true }));
                passwordInput.dispatchEvent(new Event("input", { bubbles: true }));
                form.submit();
            }""",
            {
                "username": username,
                "password": password,
                "formSelector": InstizParser.LOGIN_FORM_SELECTOR,
                "usernameSelector": InstizParser.LOGIN_USERNAME_SELECTOR,
                "passwordSelector": InstizParser.LOGIN_PASSWORD_SELECTOR,
            }
        )

    def _wait_for_login_response(self, page: Page) -> None:
        """로그인 iframe 응답이나 쿠키 반영을 잠시 기다립니다."""
        for _ in range(20):
            page.wait_for_timeout(500)
            if self._is_logged_in(page):
                return

            message = self._extract_login_response_message(page)
            if message:
                return

    def _extract_login_response_message(self, page: Page) -> str:
        """숨겨진 로그인 iframe에 표시된 오류/안내 메시지를 추출."""
        messages = []
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            if "login_check" not in frame.url and frame.name != "ifrm_login":
                continue
            try:
                text = frame.locator("body").inner_text(timeout=1000).strip()
                if text:
                    messages.append(text)
            except Exception:
                pass

            try:
                html = frame.content()
                for token in ["alert(", "ialert(", "parent.alert("]:
                    if token not in html:
                        continue
                    start = html.find(token) + len(token)
                    snippet = html[start:start + 300].strip()
                    if snippet:
                        messages.append(snippet)
            except Exception:
                pass

        cleaned_messages = []
        for message in messages:
            message = " ".join(message.split())
            if len(message) > 250:
                message = message[:250] + "..."
            if message and message not in cleaned_messages:
                cleaned_messages.append(message)

        return " | ".join(cleaned_messages)

    def _is_logged_in(self, page: Page) -> bool:
        """현재 페이지가 로그인 상태인지 확인."""
        try:
            logout_locator = page.locator(InstizParser.LOGOUT_SELECTOR)
            for idx in range(logout_locator.count()):
                if logout_locator.nth(idx).is_visible():
                    return True
        except Exception:
            pass

        try:
            body_text = page.locator("body").inner_text(timeout=3000)
            if "로그아웃" in body_text:
                return True
            if "검색은 회원만 할 수 있어요" in body_text:
                return False
        except Exception:
            pass

        return False

    def _has_search_access(self, page: Page) -> bool:
        """회원 전용 검색 페이지 접근 가능 여부로 로그인 상태를 보조 판정."""
        try:
            board_config = config.BOARDS[0] if getattr(config, "BOARDS", []) else {}
            board = board_config.get("board", "name_beauty")
            params = {"k": "test"}
            if not getattr(config, "SEARCH_ALL_BOARDS", False):
                params["id"] = board
            url = f"{config.BASE_URL}/popup_search.htm?{urlencode(params)}"
            page.goto(url, wait_until="domcontentloaded", timeout=config.BROWSER_TIMEOUT)
            self._wait_for_login_ready(page)
            body_text = page.locator("body").inner_text(timeout=5000)
            if "검색은 회원만 할 수 있어요" in body_text or "로그인 후 이용" in body_text:
                return False
            if "검색 결과" in body_text or "검색" in body_text:
                logger.info("검색 페이지 접근 확인")
                return True
        except Exception as e:
            logger.debug(f"검색 접근 확인 실패: {str(e)}")

        return False

    def _save_login_state(self) -> None:
        """로그인 세션을 파일에 저장."""
        if not getattr(config, "SAVE_LOGIN_STATE", True):
            return
        storage_path = self._resolve_storage_path()
        if not storage_path:
            return
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.context.storage_state(path=str(storage_path))
        logger.info(f"로그인 세션 저장: {storage_path}")

    @staticmethod
    def _resolve_storage_path() -> Optional[Path]:
        """세션 파일 경로를 크롤러 폴더 기준으로 해석."""
        storage_state_value = getattr(config, "LOGIN_STORAGE_STATE", "")
        if not storage_state_value:
            return None
        storage_path = Path(storage_state_value)
        if storage_path.is_absolute():
            return storage_path
        return Path(__file__).resolve().parent / storage_path

    @staticmethod
    def _mask_username(username: str) -> str:
        """로그에 계정 전체가 남지 않도록 마스킹."""
        if not username:
            return ""
        if len(username) <= 2:
            return username[0] + "*"
        return username[:2] + "*" * max(len(username) - 2, 1)
    
    def _goto_with_retry(self, url: str) -> Optional[str]:
        """페이지 이동 후 렌더링된 HTML 반환 (재시도 로직 포함)
        
        Args:
            url: 이동할 URL
            
        Returns:
            렌더링된 HTML 문자열 또는 None
        """
        attempt = 0
        current_delay = 1.0
        
        while attempt < config.MAX_RETRY:
            page = None
            try:
                # parameters: 요청 지연
                delay = utils.get_delay(include_random=True)
                time.sleep(delay)
                
                logger.debug(f"페이지 이동: {url} (시도 {attempt + 1}/{config.MAX_RETRY})")
                
                # parameters: 새 페이지 생성
                page = self.context.new_page()
                
                # parameters: 페이지 이동
                page.goto(url, wait_until="domcontentloaded", timeout=config.BROWSER_TIMEOUT)
                
                # parameters: 네트워크 안정화 대기
                page.wait_for_load_state("networkidle", timeout=config.BROWSER_TIMEOUT)
                
                logger.debug(f"페이지 렌더링 완료: {url}")
                
                # parameters: 렌더링된 HTML 획득
                html = page.content()
                
                # parameters: HTML 저장 (옵션)
                if config.SAVE_HTML:
                    self._save_html(html, f"page_{url.split('/')[-1][:50]}.html")
                
                return html
            
            except Exception as e:
                attempt += 1
                error_type = type(e).__name__
                
                if attempt >= config.MAX_RETRY:
                    logger.error(
                        f"최대 재시도 {config.MAX_RETRY}회 초과: {url} - [{error_type}] {str(e)}"
                    )
                    self.crawl_log.retries += 1
                    error_msg = f"URL: {url}, Error: {str(e)}"
                    self.crawl_log.errors.append(error_msg)
                    return None
                
                logger.warning(
                    f"재시도 {attempt}/{config.MAX_RETRY} ({current_delay:.1f}초 후): {url} - [{error_type}]"
                )
                time.sleep(current_delay)
                current_delay *= 1.5
            
            finally:
                # parameters: 페이지 종료
                if page:
                    try:
                        page.close()
                    except Exception as e:
                        logger.warning(f"페이지 종료 실패: {str(e)}")
        
        return None
    
    def fetch_board_list(
        self,
        board: str,
        category: int,
        page: int
    ) -> List[tuple]:
        """게시판 목록 페이지 요청
        
        Args:
            board: 게시판 이름
            category: 카테고리 번호
            page: 페이지 번호
            
        Returns:
            파싱된 게시글 정보 리스트
        """
        # parameters: URL 생성
        url = f"{config.BASE_URL}/{board}?page={page}&category={category}"
        
        # parameters: 캐시 확인
        if config.USE_CACHE and url in self.url_cache:
            logger.debug(f"캐시 사용: {url}")
            return self.url_cache[url]
        
        logger.debug(f"게시판 목록 요청: {url}")
        
        # parameters: 페이지 이동 및 HTML 획득
        html = self._goto_with_retry(url)
        if not html:
            return []
        
        # parameters: 파싱
        posts = InstizParser.parse_board_list(html, board, category)
        
        # parameters: 캐시에 저장
        if config.USE_CACHE:
            self.url_cache[url] = posts
        
        return posts

    def fetch_search_results(
        self,
        board: str,
        category: int,
        keyword: str,
        max_more_clicks: int = None,
        max_posts: int = None
    ) -> List[tuple]:
        """검색 키워드 기반 게시글 목록 요청.

        인스티즈 검색 결과는 페이지네이션 대신 더보기로 확장되는 화면이 있을 수 있어,
        Playwright 페이지를 유지한 채 더보기 버튼 후보를 반복 클릭한 뒤 최종 HTML을 파싱합니다.
        """
        url = self.build_search_url(board, category, keyword)
        cache_key = f"search::{url}::more={max_more_clicks or config.MAX_MORE_CLICKS}"

        if config.USE_CACHE and cache_key in self.url_cache:
            logger.debug(f"캐시 사용: {cache_key}")
            return self.url_cache[cache_key]

        logger.info(f"검색 결과 요청: board={board}, category={category}, keyword={keyword}")
        html = self._goto_search_with_more(
            url=url,
            board=board,
            category=category,
            keyword=keyword,
            max_more_clicks=max_more_clicks if max_more_clicks is not None else config.MAX_MORE_CLICKS,
            max_posts=max_posts if max_posts is not None else config.MAX_SEARCH_POSTS,
        )
        if not html:
            return []

        posts = InstizParser.parse_search_results(html, board, category, keyword)
        if max_posts:
            posts = posts[:max_posts]

        if config.USE_CACHE:
            self.url_cache[cache_key] = posts

        return posts

    def _goto_search_with_more(
        self,
        url: str,
        board: str,
        category: int,
        keyword: str,
        max_more_clicks: int,
        max_posts: int
    ) -> Optional[str]:
        """검색 결과로 이동한 뒤 더보기를 반복 클릭하고 HTML을 반환."""
        page = None
        try:
            time.sleep(utils.get_delay(include_random=True))
            page = self.context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=config.BROWSER_TIMEOUT)
            self._wait_for_search_ready(page)

            previous_count = self._search_result_count(page, board, category, keyword)
            logger.info(f"검색 초기 결과: keyword={keyword}, posts={previous_count}")

            for click_idx in range(max_more_clicks):
                if max_posts and previous_count >= max_posts:
                    break

                clicked = self._click_more_button(page)
                if not clicked:
                    logger.debug(f"더보기 버튼 없음: keyword={keyword}, click={click_idx}")
                    break

                page.wait_for_timeout(int(utils.get_delay(include_random=True) * 1000))
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

                current_count = self._search_result_count(page, board, category, keyword)
                logger.info(
                    f"더보기 클릭: keyword={keyword}, click={click_idx + 1}, "
                    f"posts={current_count}"
                )
                if current_count <= previous_count:
                    break
                previous_count = current_count

            html = page.content()
            if config.SAVE_HTML:
                safe_keyword = utils.safe_filename(keyword)
                self._save_html(html, f"search_{safe_keyword}.html")
            return html
        except Exception as e:
            logger.error(f"검색 결과 수집 실패: {url} - {str(e)}")
            self.crawl_log.errors.append(f"Search URL: {url}, Error: {str(e)}")
            return None
        finally:
            if page:
                try:
                    page.close()
                except Exception as e:
                    logger.warning(f"검색 페이지 종료 실패: {str(e)}")

    def _wait_for_search_ready(self, page: Page) -> None:
        """검색 결과 페이지가 파싱 가능한 상태가 될 때까지만 짧게 대기."""
        try:
            page.wait_for_selector("body", timeout=5000)
        except Exception:
            logger.debug("검색 페이지 body 대기 timeout, 현재 DOM으로 계속 진행")

        try:
            result_selectors = ", ".join(InstizParser.SELECTORS["search"]["result_links"])
            page.wait_for_selector(result_selectors, timeout=5000)
        except Exception:
            logger.debug("검색 결과 링크 대기 timeout, 현재 DOM으로 계속 진행")

        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            logger.debug("검색 페이지 networkidle 대기 timeout, 현재 DOM으로 계속 진행")

    def _search_result_count(self, page: Page, board: str, category: int, keyword: str) -> int:
        """현재 검색 결과 HTML에서 파싱 가능한 게시글 수를 반환."""
        try:
            return len(InstizParser.parse_search_results(page.content(), board, category, keyword))
        except Exception:
            return 0

    def _click_more_button(self, page: Page) -> bool:
        """parser.py의 selector 후보를 사용해 더보기 버튼을 클릭."""
        for selector in InstizParser.more_button_selectors():
            try:
                locator = page.locator(selector)
                count = locator.count()
                for idx in range(count):
                    target = locator.nth(idx)
                    if not target.is_visible():
                        continue
                    text = (target.inner_text(timeout=1000) or "").strip()
                    if "더보기" not in text and "more" not in selector.lower():
                        continue
                    target.scroll_into_view_if_needed(timeout=3000)
                    target.click(timeout=5000)
                    return True
            except Exception:
                continue

        # Fallback: text 기반 selector가 태그 구조 변경에도 버티도록 마지막에 시도합니다.
        try:
            target = page.get_by_text("더보기").last
            if target.is_visible():
                target.scroll_into_view_if_needed(timeout=3000)
                target.click(timeout=5000)
                return True
        except Exception:
            return False

        return False

    def build_search_url(self, board: str, category: int, keyword: str) -> str:
        """검색 결과 URL 생성."""
        search_all_boards = getattr(config, "SEARCH_ALL_BOARDS", False) or not board
        if config.SEARCH_ENDPOINT == "board" and not search_all_boards:
            params = {
                "k": keyword,
                "id": board,
                "stype": config.SEARCH_TYPE,
                "category": category,
            }
            return f"{config.BASE_URL}/bbs/list.php?{urlencode(params)}"

        params = {"k": keyword}
        if board and not search_all_boards:
            params["id"] = board
        return f"{config.BASE_URL}/popup_search.htm?{urlencode(params)}"
    
    def fetch_post_detail(self, post_url: str) -> tuple:
        """게시글 상세 페이지 요청
        
        Args:
            post_url: 게시글 URL
            
        Returns:
            (content_text, image_count, comments) 튜플
        """
        # parameters: 캐시 확인
        if config.USE_CACHE and post_url in self.url_cache:
            logger.debug(f"캐시 사용: {post_url}")
            return self.url_cache[post_url]
        
        logger.debug(f"게시글 상세 요청: {post_url}")
        
        # parameters: 페이지 이동 및 HTML 획득
        html = self._goto_with_retry(post_url)
        if not html:
            return None, 0, []
        
        # parameters: 파싱
        content_text, image_count = InstizParser.parse_post_detail(html)
        
        # parameters: 댓글 파싱
        comments = InstizParser.parse_comments(html) if config.CRAWL_COMMENT else []
        
        result = (content_text, image_count, comments)
        
        # parameters: 캐시에 저장
        if config.USE_CACHE:
            self.url_cache[post_url] = result
        
        return result
    
    def crawl_board(
        self,
        board: str,
        category: int,
        start_page: int,
        end_page: int
    ) -> tuple:
        """게시판 크롤링 (게시글 링크 수집 단계)
        
        Args:
            board: 게시판 이름
            category: 카테고리 번호
            start_page: 시작 페이지
            end_page: 종료 페이지
            
        Returns:
            (Post 리스트, 댓글 정보 딕셔너리)
        """
        posts = []
        post_details = {}
        
        logger.info(f"게시판 크롤링 시작: {board} (카테고리: {category})")
        
        # parameters: 게시판 페이지 순회
        from tqdm import tqdm
        
        for page in tqdm(
            range(start_page, end_page + 1),
            desc=f"[{board}] 페이지",
            disable=not config.SHOW_PROGRESS
        ):
            page_posts = self.fetch_board_list(board, category, page)
            self.crawl_log.pages += 1
            
            if not page_posts:
                logger.warning(f"페이지 {page}에서 게시글을 찾을 수 없음")
                continue
            
            # parameters: 게시글 객체 생성
            for post_info in page_posts:
                post_id, title, author, post_url, comment_count, view_count, like_count, created_date, has_image = post_info
                
                # parameters: 중복 확인
                if post_id in self.processed_posts:
                    logger.debug(f"이미 처리된 게시글: {post_id}")
                    continue
                
                self.processed_posts.add(post_id)
                
                post = Post(
                    post_id=post_id,
                    board=board,
                    category=category,
                    title=title,
                    author=author,
                    comment_count=comment_count,
                    view_count=view_count,
                    like_count=like_count,
                    created_date=created_date,
                    has_image=has_image,
                    image_count=0,
                    post_url=post_url
                )
                
                posts.append(post)
                post_details[post.post_id] = {"post": post, "comments": []}
            
            self.crawl_log.posts += len(page_posts)
        
        logger.info(f"게시판 크롤링 완료: {len(posts)}개 게시글 수집")
        
        return posts, post_details

    def crawl_search(
        self,
        board: str,
        category: int,
        keyword: str,
        max_more_clicks: int = None,
        max_posts: int = None
    ) -> tuple:
        """검색 키워드 기반 크롤링."""
        posts = []
        post_details = {}

        logger.info(f"검색 크롤링 시작: board={board}, category={category}, keyword={keyword}")
        page_posts = self.fetch_search_results(board, category, keyword, max_more_clicks, max_posts)
        self.crawl_log.pages += 1

        for post_info in page_posts:
            post_id, title, author, post_url, comment_count, view_count, like_count, created_date, has_image = post_info
            post_board = board or InstizParser.extract_board_name(post_url) or "search"
            processed_key = f"{post_board}:{post_id}"
            if processed_key in self.processed_posts:
                continue

            self.processed_posts.add(processed_key)
            post = Post(
                post_id=post_id,
                board=post_board,
                category=category if board else 0,
                title=title,
                author=author,
                comment_count=comment_count,
                view_count=view_count,
                like_count=like_count,
                created_date=created_date,
                has_image=has_image,
                image_count=0,
                post_url=post_url
            )
            posts.append(post)
            post_details[post.post_id] = {"post": post, "comments": []}

        self.crawl_log.posts += len(posts)
        logger.info(f"검색 크롤링 완료: keyword={keyword}, posts={len(posts)}")
        return posts, post_details
    
    def crawl_post_contents(
        self,
        posts: List[Post]
    ) -> dict:
        """게시글 본문 및 댓글 수집 (순차 처리)
        
        Args:
            posts: Post 리스트
            
        Returns:
            게시글 상세 정보 딕셔너리
        """
        if not config.CRAWL_CONTENT:
            logger.info("본문 수집 스킵 (CRAWL_CONTENT=False)")
            return {}
        
        logger.info(f"게시글 본문 수집 시작: {len(posts)}개 게시글")
        
        post_details = {}
        
        # parameters: 순차 처리로 변경 (Playwright는 스레드 불안전)
        from tqdm import tqdm
        
        for post in tqdm(
            posts,
            desc="게시글 본문",
            disable=not config.SHOW_PROGRESS
        ):
            try:
                # parameters: 게시글 상세 정보 수집
                result = self.fetch_post_detail(post.post_url)
                
                if result:
                    content_text, image_count, comments = result
                    
                    post.content = content_text
                    post.image_count = image_count
                    
                    post_details[post.post_id] = {
                        "post": post,
                        "comments": comments
                    }
                    
                    self.crawl_log.comments += len(comments)
                else:
                    post_details[post.post_id] = {
                        "post": post,
                        "comments": []
                    }
            
            except Exception as e:
                logger.error(f"게시글 본문 수집 실패: {post.post_url} - {str(e)}")
                error_msg = f"Post URL: {post.post_url}, Error: {str(e)}"
                self.crawl_log.errors.append(error_msg)
                
                post_details[post.post_id] = {
                    "post": post,
                    "comments": []
                }
        
        logger.info(f"게시글 본문 수집 완료: {len(post_details)}개 게시글")
        
        return post_details
    
    def _save_html(self, html: str, filename: str) -> None:
        """HTML 파일 저장
        
        Args:
            html: HTML 문자열
            filename: 파일명
        """
        html_dir = Path("html")
        html_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = html_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            logger.debug(f"HTML 저장: {filepath}")
        except Exception as e:
            logger.error(f"HTML 저장 실패: {filepath} - {str(e)}")
    
    def get_statistics(self) -> dict:
        """크롤링 통계 반환
        
        Returns:
            통계 딕셔너리
        """
        self.crawl_log.end_time = datetime.now()
        runtime = (self.crawl_log.end_time - self.crawl_log.start_time).total_seconds()
        
        return {
            "start_time": self.crawl_log.start_time.isoformat(),
            "end_time": self.crawl_log.end_time.isoformat(),
            "runtime": utils.format_runtime(runtime),
            "boards": 1,
            "pages": self.crawl_log.pages,
            "posts": self.crawl_log.posts,
            "comments": self.crawl_log.comments,
            "errors": len(self.crawl_log.errors),
            "retries": self.crawl_log.retries,
            "average_speed": f"{self.crawl_log.posts / max(runtime, 1):.2f} 게시글/초"
        }
