"""Playwright-based Daum Cafe all-board search crawler."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

import config
from models import Comment, CrawlStats, Post
from parser import parse_post_detail, parse_search_results
from utils import (
    ensure_directories,
    load_existing_comments,
    load_existing_posts,
    merge_comments,
    merge_posts,
    polite_sleep,
    search_comment_csv_path,
    search_post_csv_path,
    write_comments,
    write_posts,
)


@dataclass(slots=True)
class RuntimeConfig:
    search_keywords: list[str]
    search_start_date: date
    search_end_date: date
    search_start_page: int
    search_list_size: int
    checkpoint_size: int
    crawl_details: bool
    save_html: bool
    login_enabled: bool
    login_storage_state: Path
    save_login_state: bool
    manual_login_wait_seconds: int
    headless: bool
    browser_timeout: int
    request_delay: float
    random_delay_rate: float
    max_retry: int
    base_url: str
    cafe_code: str
    grpid: str
    headers: dict[str, str]
    output_dir: Path
    log_dir: Path
    html_dir: Path


class DaumCafeCrawler:
    """Collect date-bounded all-board Daum Cafe search results."""

    def __init__(self, runtime: RuntimeConfig, logger: logging.Logger) -> None:
        self.runtime = runtime
        self.logger = logger
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        ensure_directories(runtime.output_dir, runtime.log_dir, runtime.html_dir, runtime.login_storage_state.parent)

    def start_browser(self) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.runtime.headless)
        context_options: dict[str, object] = {"user_agent": self.runtime.headers["User-Agent"]}
        if self.runtime.login_storage_state.exists():
            context_options["storage_state"] = str(self.runtime.login_storage_state)
            self.logger.info("Saved Daum login session loaded")
        self.context = self.browser.new_context(**context_options)

    def close_browser(self) -> None:
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.context = self.browser = self.playwright = None

    def login(self) -> None:
        """
        storage_state 방식만 사용.
        세션이 없으면 에러를 발생시킨다.
        """

        if not self.context:
            raise RuntimeError("Browser has not been started")

        if self.runtime.login_storage_state.exists():
            self.logger.info("Saved login session loaded.")
            return

        raise RuntimeError(
            "\n저장된 로그인 세션이 없습니다.\n"
            "먼저 python login_once.py 를 실행하여 로그인 세션을 생성하세요."
        )

    def crawl_search(self) -> CrawlStats:
        """Crawl every configured keyword, saving completed 50-post batches."""
        if not self.context:
            raise RuntimeError("Browser has not been started")
        stat = CrawlStats(board="search")
        post_path = search_post_csv_path(self.runtime.output_dir, self.runtime.search_start_date, self.runtime.search_end_date)
        comment_path = search_comment_csv_path(self.runtime.output_dir, self.runtime.search_start_date, self.runtime.search_end_date)
        posts_by_key = {self._post_key(post): post for post in load_existing_posts(post_path)}
        comments = load_existing_comments(comment_path)
        pending: list[Post] = []
        dirty = False

        def checkpoint() -> None:
            nonlocal comments, dirty
            if not pending:
                return
            batch = pending[:]
            pending.clear()
            batch_comments: list[Comment] = []
            if self.runtime.crawl_details:
                batch, batch_comments = self._enrich_posts(batch)
            for post in batch:
                posts_by_key[self._post_key(post)] = post
            comments = merge_comments(comments, batch_comments)
            write_posts(post_path, merge_posts([], list(posts_by_key.values())))
            if self.runtime.crawl_details:
                write_comments(comment_path, comments)
            dirty = False
            self.logger.info("Checkpoint saved: posts=%s comments=%s", len(posts_by_key), len(comments))

        try:
            for keyword in self.runtime.search_keywords:
                self.logger.info("Search start: keyword=%s", keyword)
                page_number = self.runtime.search_start_page
                reached_start_date = False
                while not reached_start_date:
                    html = self.fetch_search_page(keyword, page_number)
                    page_posts = parse_search_results(html, self.runtime.base_url, keyword)
                    stat.pages += 1
                    if not page_posts:
                        break
                    for post in page_posts:
                        post_date = self._post_date(post.date)
                        if post_date is None:
                            self.logger.warning("Skipping undated result: %s", post.link)
                            continue
                        if post_date > self.runtime.search_end_date:
                            continue
                        if post_date < self.runtime.search_start_date:
                            reached_start_date = True
                            break
                        key = self._post_key(post)
                        existing = posts_by_key.get(key)
                        if existing:
                            existing.search_keywords = self._combine_keywords(existing.search_keywords, keyword)
                            dirty = True
                            continue
                        duplicate = next((item for item in pending if self._post_key(item) == key), None)
                        if duplicate:
                            duplicate.search_keywords = self._combine_keywords(duplicate.search_keywords, keyword)
                            continue
                        pending.append(post)
                        stat.posts += 1
                        if len(pending) >= self.runtime.checkpoint_size:
                            checkpoint()
                    page_number += 1
        except KeyboardInterrupt:
            self.logger.warning("Interrupted; saving completed and pending work")
        except Exception:
            stat.errors += 1
            self.logger.exception("Search crawl failed")
        finally:
            checkpoint()
            if dirty:
                write_posts(post_path, merge_posts([], list(posts_by_key.values())))
        stat.comments = len(comments)
        return stat

    def fetch_search_page(self, keyword: str, page_number: int) -> str:
        """Navigate a search result page in the authenticated browser context."""
        if not self.context:
            raise RuntimeError("Browser has not been started")
        url = self.search_url(keyword, page_number)
        last_error: Exception | None = None
        for attempt in range(1, self.runtime.max_retry + 1):
            page: Page | None = None
            try:
                page = self.context.new_page()
                page.goto(url, wait_until="networkidle")

                # iframe 로드 대기
                page.wait_for_selector("iframe#down", timeout=10000)

                frame = page.frame_locator("iframe#down")

                # 검색 결과가 나타날 때까지 대기
                frame.locator("body").wait_for(timeout=10000)

                html = frame.locator("body").inner_html()

                Path("debug_search.html").write_text(
                    html,
                    encoding="utf-8"
                )

                return html
            except Exception as exc:
                last_error = exc
                self.logger.warning("Search retry %s/%s page=%s: %s", attempt, self.runtime.max_retry, page_number, exc)
            finally:
                if page:
                    page.close()
        raise RuntimeError(f"Search request failed: {url}") from last_error

    def _enrich_posts(self, posts: list[Post]) -> tuple[list[Post], list[Comment]]:
        enriched: list[Post] = []
        comments: list[Comment] = []
        for post in posts:
            page: Page | None = None
            try:
                page = self.context.new_page() if self.context else None
                if page is None:
                    raise RuntimeError("Browser has not been started")
                page.goto(
                    post.link,
                    wait_until="networkidle",
                    timeout=self.runtime.browser_timeout,
                )

                # iframe이 있는 경우
                iframe = page.locator("iframe#down")

                if iframe.count() > 0:
                    frame = page.frame_locator("iframe#down")

                    frame.locator("body").wait_for(timeout=10000)

                    html = frame.locator("body").inner_html()
                else:
                    html = page.content()

                updated, post_comments = parse_post_detail(html, post)  

                self.logger.info(
                    "Detail parsed: %s comments=%d",
                    post.post_id,
                    len(post_comments),
                )
                if not Path("debug_detail.html").exists():
                    Path("debug_detail.html").write_text(
                        html,
                        encoding="utf-8"
                    )
                enriched.append(updated)
                comments.extend(post_comments)
            except Exception as exc:
                self.logger.warning("Detail unavailable; preview retained: %s (%s)", post.link, exc)
                enriched.append(post)
            finally:
                if page:
                    page.close()
                polite_sleep(self.runtime.request_delay, self.runtime.random_delay_rate)
        return enriched, comments

    def search_url(self, keyword: str, page_number: int) -> str:
        params = {
            "grpid": self.runtime.grpid,
            "item": "subject",
            "sorttype": "0",
            "query": keyword,
            "pagenum": page_number,
            "listnum": self.runtime.search_list_size,
        }
        return f"{self.runtime.base_url}/_c21_/cafesearch?{urlencode(params)}"

    def _has_cafe_session(self, page: Page) -> bool:
        page.goto(f"{self.runtime.base_url}/{self.runtime.cafe_code}", wait_until="domcontentloaded", timeout=self.runtime.browser_timeout)
        try:
            return page.locator("#loginout").inner_text(timeout=3_000).strip() == "로그아웃"
        except Exception:
            return "로그아웃" in page.locator("body").inner_text(timeout=3_000)

    def _login_url(self) -> str:
        return "https://logins.daum.net/accounts/loginform.do?" + urlencode({"url": f"{self.runtime.base_url}/{self.runtime.cafe_code}"})

    def _save_login_state(self) -> None:
        if self.context and self.runtime.save_login_state:
            self.context.storage_state(path=str(self.runtime.login_storage_state))

    @staticmethod
    def _fill_first(page: Page, selector: str, value: str) -> None:
        locator = page.locator(selector)
        if locator.count() == 0:
            raise RuntimeError(f"Daum login input not found: {selector}")
        locator.first.fill(value)

    @staticmethod
    def _post_key(post: Post) -> str:
        return f"{post.board}:{post.post_id or post.number}"

    @staticmethod
    def _combine_keywords(current: str, keyword: str) -> str:
        return ",".join(sorted({item for item in [*current.split(","), keyword] if item}))

    @staticmethod
    def _post_date(value: str) -> date | None:
        try:
            return datetime.strptime(value, "%y.%m.%d").date()
        except ValueError:
            return None


def build_runtime_config(
    keywords: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    crawl_details: bool | None = None,
    headless: bool | None = None,
) -> RuntimeConfig:
    """Merge CLI overrides with config.py and validate date boundaries."""
    start = datetime.strptime(start_date or config.SEARCH_START_DATE, "%Y-%m-%d").date()
    end = datetime.strptime(end_date or config.SEARCH_END_DATE, "%Y-%m-%d").date()
    if start > end:
        raise ValueError("SEARCH_START_DATE must be on or before SEARCH_END_DATE")
    effective_keywords = [value.strip() for value in (keywords or config.SEARCH_KEYWORDS) if value.strip()]
    if not effective_keywords:
        raise ValueError("At least one search keyword is required")
    return RuntimeConfig(
        search_keywords=effective_keywords,
        search_start_date=start,
        search_end_date=end,
        search_start_page=config.SEARCH_START_PAGE,
        search_list_size=config.SEARCH_LIST_SIZE,
        checkpoint_size=config.CHECKPOINT_SIZE,
        crawl_details=config.CRAWL_DETAILS if crawl_details is None else crawl_details,
        save_html=config.SAVE_HTML,
        login_enabled=config.LOGIN_ENABLED,
        login_storage_state=config.PROJECT_DIR / config.LOGIN_STORAGE_STATE,
        save_login_state=config.SAVE_LOGIN_STATE,
        manual_login_wait_seconds=config.MANUAL_LOGIN_WAIT_SECONDS,
        headless=config.HEADLESS if headless is None else headless,
        browser_timeout=config.BROWSER_TIMEOUT,
        request_delay=config.REQUEST_DELAY,
        random_delay_rate=config.RANDOM_DELAY_RATE,
        max_retry=config.MAX_RETRY,
        base_url=config.BASE_URL,
        cafe_code=config.CAFE_CODE,
        grpid=config.GRPID,
        headers=config.HEADERS,
        output_dir=config.OUTPUT_DIR,
        log_dir=config.LOG_DIR,
        html_dir=config.HTML_DIR,
    )
