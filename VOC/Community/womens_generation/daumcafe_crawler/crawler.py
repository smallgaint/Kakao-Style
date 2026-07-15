"""HTTP and orchestration layer for the Daum Cafe crawler."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse, urlunparse, parse_qs

import requests
from tqdm import tqdm

import config
from models import Comment, CrawlStats, Post
from parser import extract_contentval, extract_iframe_src, parse_board_posts, parse_post_detail, validate_selectors
from utils import (
    cache_path,
    comment_csv_path,
    ensure_directories,
    load_existing_comments,
    load_existing_posts,
    merge_comments,
    merge_posts,
    polite_sleep,
    post_csv_path,
    write_comments,
    write_posts,
)


@dataclass(slots=True)
class RuntimeConfig:
    """Effective settings after config.py and CLI arguments are merged."""

    boards: list[str]
    start_page: int
    end_page: int
    crawl_content: bool
    crawl_comment: bool
    only_new_posts: bool
    save_html: bool
    use_cache: bool
    request_delay: float
    random_delay_rate: float
    max_retry: int
    thread_workers: int
    timeout: int
    base_url: str
    cafe_code: str
    grpid: str
    headers: dict[str, str]
    output_dir: Path
    log_dir: Path
    html_dir: Path
    cache_dir: Path


class DaumCafeCrawler:
    """Collect Daum Cafe board posts and optional detail/comment data."""

    def __init__(self, runtime: RuntimeConfig, logger: logging.Logger) -> None:
        self.runtime = runtime
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(runtime.headers)
        ensure_directories(runtime.output_dir, runtime.log_dir, runtime.html_dir, runtime.cache_dir)

    def crawl_all(self) -> list[CrawlStats]:
        """Crawl every configured board."""
        stats: list[CrawlStats] = []
        for board in self.runtime.boards:
            stats.append(self.crawl_board(board))
        return stats

    def crawl_board(self, board: str) -> CrawlStats:
        """Crawl one board over the configured page range."""
        started = time.perf_counter()
        stat = CrawlStats(board=board)
        post_path = post_csv_path(self.runtime.output_dir, board, self.runtime.start_page, self.runtime.end_page)
        comment_path = comment_csv_path(self.runtime.output_dir, board, self.runtime.start_page, self.runtime.end_page)
        existing_posts = load_existing_posts(post_path)
        existing_comments = load_existing_comments(comment_path)
        existing_keys = {post.post_id or post.number for post in existing_posts}
        collected: dict[str, Post] = {}

        self.logger.info("Start board=%s pages=%s-%s", board, self.runtime.start_page, self.runtime.end_page)
        try:
            for page in tqdm(range(self.runtime.start_page, self.runtime.end_page + 1), desc=f"{board} pages"):
                html = self.fetch_board_frame(board, page)
                self.log_selector_validation(html, f"{board} page={page}")
                page_posts = parse_board_posts(html, board, self.runtime.base_url)
                for post in page_posts:
                    key = post.post_id or post.number
                    if self.runtime.only_new_posts and key in existing_keys:
                        continue
                    collected[key] = post
                stat.pages += 1
                self.logger.info("Page complete board=%s page=%s posts=%s", board, page, len(page_posts))
        except KeyboardInterrupt:
            self.logger.warning("Graceful shutdown requested; saving collected rows.")
        except Exception as exc:
            stat.errors += 1
            self.logger.exception("Board crawl failed board=%s error=%s", board, exc)

        posts_to_enrich = list(collected.values())
        new_comments: list[Comment] = []
        if self.runtime.crawl_content:
            posts_to_enrich, new_comments = self.enrich_posts(posts_to_enrich)

        posts = merge_posts(existing_posts, posts_to_enrich)
        comments = merge_comments(existing_comments, new_comments)
        write_posts(post_path, posts)
        if self.runtime.crawl_content and self.runtime.crawl_comment:
            write_comments(comment_path, comments)

        stat.posts = len(posts_to_enrich)
        stat.comments = len(new_comments)
        elapsed = time.perf_counter() - started
        self.logger.info(
            "End board=%s pages=%s posts=%s comments=%s elapsed=%.2fs",
            board,
            stat.pages,
            stat.posts,
            stat.comments,
            elapsed,
        )
        return stat

    def enrich_posts(self, posts: list[Post]) -> tuple[list[Post], list[Comment]]:
        """Fetch article detail pages in parallel."""
        if not posts:
            return [], []
        enriched: list[Post] = []
        comments: list[Comment] = []
        with ThreadPoolExecutor(max_workers=self.runtime.thread_workers) as executor:
            futures = {executor.submit(self.fetch_post_detail, post): post for post in posts}
            for future in tqdm(as_completed(futures), total=len(futures), desc="post details"):
                original = futures[future]
                try:
                    post, post_comments = future.result()
                    enriched.append(post)
                    if self.runtime.crawl_comment:
                        comments.extend(post_comments)
                except Exception as exc:
                    self.logger.exception("Detail failed link=%s error=%s", original.link, exc)
                    enriched.append(original)
        return enriched, comments

    def fetch_board_frame(self, board: str, page: int) -> str:
        """Fetch the outer board page, extract iframe src, then fetch the iframe."""
        outer_url = self.board_outer_url(board)
        outer_html = self.fetch_text(outer_url)
        frame_url = extract_iframe_src(outer_html, self.runtime.base_url) or self.board_frame_url(board, page)
        frame_url = self.with_page(frame_url, page)
        return self.fetch_text(frame_url)

    def fetch_post_detail(self, post: Post) -> tuple[Post, list[Comment]]:
        """Fetch the article iframe and parse detail data."""
        html = self.fetch_detail_frame(post)
        if self.runtime.save_html:
            self.save_html(post, html)
        return parse_post_detail(html, post)

    def fetch_detail_frame(self, post: Post) -> str:
        """Resolve outer article URLs to iframe detail URLs."""
        if "_c21_/bbs_read" in post.link:
            return self.fetch_text(post.link)
        outer_html = self.fetch_text(post.link)
        frame_url = extract_iframe_src(outer_html, self.runtime.base_url)
        if not frame_url:
            frame_url = self.detail_frame_url(post)
        return self.fetch_text(frame_url)

    def fetch_text(self, url: str) -> str:
        """Fetch HTML with retry, optional URL cache, and random delay."""
        cached = cache_path(self.runtime.cache_dir, url)
        if self.runtime.use_cache and cached.exists():
            return cached.read_text(encoding="utf-8")

        last_error: Exception | None = None
        for attempt in range(1, self.runtime.max_retry + 1):
            try:
                response = self.session.get(url, timeout=self.runtime.timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or "utf-8"
                polite_sleep(self.runtime.request_delay, self.runtime.random_delay_rate)
                if self.runtime.use_cache:
                    cached.write_text(response.text, encoding="utf-8")
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                self.logger.warning("Retry %s/%s url=%s error=%s", attempt, self.runtime.max_retry, url, exc)
                polite_sleep(self.runtime.request_delay * attempt, self.runtime.random_delay_rate)
        raise RuntimeError(f"Request failed after retries: {url}") from last_error

    def board_outer_url(self, board: str) -> str:
        """Build a human-facing board URL."""
        return f"{self.runtime.base_url}/{self.runtime.cafe_code}/{board}"

    def board_frame_url(self, board: str, page: int) -> str:
        """Build the Daum Cafe board iframe URL."""
        query = urlencode({"grpid": self.runtime.grpid, "fldid": board, "page": page})
        return f"{self.runtime.base_url}/_c21_/bbs_list?{query}"

    def detail_frame_url(self, post: Post) -> str:
        """Build a best-effort detail iframe URL from a post link."""
        contentval = extract_contentval(post.link)
        params = {"grpid": self.runtime.grpid, "fldid": post.board, "datanum": post.post_id or post.number}
        if contentval:
            params["contentval"] = contentval
        return f"{self.runtime.base_url}/_c21_/bbs_read?{urlencode(params)}"

    def with_page(self, url: str, page: int) -> str:
        """Set or replace the page query parameter on an iframe URL."""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["page"] = [str(page)]
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    def save_html(self, post: Post, html: str) -> None:
        """Save original article HTML for auditing."""
        board_dir = self.runtime.html_dir / post.board
        ensure_directories(board_dir)
        (board_dir / f"{post.number}.html").write_text(html, encoding="utf-8")

    def log_selector_validation(self, html: str, label: str) -> None:
        """Log missing selector groups without failing the crawl."""
        status = validate_selectors(html)
        for key, ok in status.items():
            if not ok and key == "board_rows":
                self.logger.warning("Selector not found label=%s selector_group=%s", label, key)


def build_runtime_config(
    boards: list[str] | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
    crawl_content: bool | None = None,
    crawl_comment: bool | None = None,
    save_html: bool | None = None,
    only_new_posts: bool | None = None,
) -> RuntimeConfig:
    """Merge CLI arguments with config.py defaults."""
    effective_content = config.CRAWL_CONTENT if crawl_content is None else crawl_content
    effective_comment = config.CRAWL_COMMENT if crawl_comment is None else crawl_comment
    if not effective_content:
        effective_comment = False

    return RuntimeConfig(
        boards=boards or config.BOARDS,
        start_page=start_page or config.START_PAGE,
        end_page=end_page or config.END_PAGE,
        crawl_content=effective_content,
        crawl_comment=effective_comment,
        only_new_posts=config.ONLY_NEW_POSTS if only_new_posts is None else only_new_posts,
        save_html=config.SAVE_HTML if save_html is None else save_html,
        use_cache=config.USE_CACHE,
        request_delay=config.REQUEST_DELAY,
        random_delay_rate=config.RANDOM_DELAY_RATE,
        max_retry=config.MAX_RETRY,
        thread_workers=config.THREAD_WORKERS,
        timeout=config.TIMEOUT,
        base_url=config.BASE_URL,
        cafe_code=config.CAFE_CODE,
        grpid=config.GRPID,
        headers=config.HEADERS,
        output_dir=config.OUTPUT_DIR,
        log_dir=config.LOG_DIR,
        html_dir=config.HTML_DIR,
        cache_dir=config.CACHE_DIR,
    )
