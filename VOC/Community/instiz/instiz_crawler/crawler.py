"""
Playwright 기반 웹 크롤링 로직 전담
"""

import time
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional, List, Set
from pathlib import Path
from datetime import datetime
import logging

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
        self.processed_posts: Set[int] = set()
        
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
            self.context = self.browser.new_context(
                user_agent=config.HEADERS.get("User-Agent", "")
            )
            
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
