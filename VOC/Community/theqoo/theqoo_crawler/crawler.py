"""HTTP and orchestration logic for Theqoo crawling."""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests import Session
from tqdm import tqdm

import config
from models import Comment, CrawlStats, Post
from parser import parse_board_posts, parse_comment_json, parse_post_detail
from utils import (
    comment_csv_path,
    ensure_directories,
    load_existing_comments,
    load_existing_numbers,
    load_existing_posts,
    merge_comments,
    merge_posts,
    post_csv_path,
    write_comments,
    write_posts,
)


@dataclass(slots=True)
class RuntimeConfig:
    """Effective runtime settings after config and CLI are merged."""

    boards: list[str]
    start_page: int
    end_page: int
    crawl_content: bool
    crawl_comment: bool
    save_html: bool
    request_delay: float
    max_retry: int
    thread_workers: int
    timeout: int
    base_url: str
    headers: dict[str, str]
    output_dir: Path
    log_dir: Path
    html_dir: Path


class TheqooCrawler:
    """Collect Theqoo board posts, optional content, and optional comments."""

    def __init__(self, runtime: RuntimeConfig, logger: logging.Logger) -> None:
        self.runtime = runtime
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(runtime.headers)
        ensure_directories(runtime.output_dir, runtime.log_dir, runtime.html_dir)

    def crawl_all(self) -> list[CrawlStats]:
        """Crawl every configured board and return crawl statistics."""
        stats: list[CrawlStats] = []
        for board in self.runtime.boards:
            stats.append(self.crawl_board(board))
        return stats

    def crawl_board(self, board: str) -> CrawlStats:
        """Crawl one board from start_page to end_page."""
        started = time.perf_counter()
        stat = CrawlStats(board=board)
        post_path = post_csv_path(self.runtime.output_dir, board, self.runtime.start_page, self.runtime.end_page)
        comment_path = comment_csv_path(self.runtime.output_dir, board, self.runtime.start_page, self.runtime.end_page)
        existing_posts = load_existing_posts(post_path)
        existing_comments = load_existing_comments(comment_path)
        existing = load_existing_numbers(post_path)
        posts_by_number: dict[str, Post] = {}

        self.logger.info("Start board=%s pages=%s-%s", board, self.runtime.start_page, self.runtime.end_page)
        page_range = range(self.runtime.start_page, self.runtime.end_page + 1)
        for page in tqdm(page_range, desc=f"{board} pages"):
            try:
                html = self.fetch_text(self.board_url(board, page))
                page_posts = parse_board_posts(html, board, self.runtime.base_url)
                for post in page_posts:
                    if post.number in existing or post.number in posts_by_number:
                        continue
                    posts_by_number[post.number] = post
                stat.pages += 1
                self.logger.info("Page complete board=%s page=%s posts=%s", board, page, len(page_posts))
            except Exception as exc:
                stat.errors += 1
                self.logger.exception("Page failed board=%s page=%s error=%s", board, page, exc)

        new_posts = list(posts_by_number.values())
        posts_to_enrich = [*new_posts, *self.posts_needing_backfill(existing_posts, existing_comments)]
        new_comments: list[Comment] = []
        if self.runtime.crawl_content:
            enriched_posts, new_comments = self.enrich_posts(posts_to_enrich)
            new_posts = enriched_posts
        elif not self.runtime.crawl_content:
            self.logger.info("Content crawl disabled; comments are skipped as required.")

        posts = merge_posts(existing_posts, new_posts)
        comments = merge_comments(existing_comments, new_comments)
        write_posts(post_path, posts)
        if self.runtime.crawl_content and self.runtime.crawl_comment:
            write_comments(comment_path, comments)

        stat.posts = len(new_posts)
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

    def posts_needing_backfill(self, posts: list[Post], comments: list[Comment]) -> list[Post]:
        """Return existing posts that need missing content or comments filled in."""
        if not self.runtime.crawl_content:
            return []
        commented_posts = {comment.post_number for comment in comments}
        targets: list[Post] = []
        for post in posts:
            needs_content = not post.content
            needs_comments = self.runtime.crawl_comment and post.comment_count > 0 and post.number not in commented_posts
            if needs_content or needs_comments:
                targets.append(post)
        return targets

    def enrich_posts(self, posts: list[Post]) -> tuple[list[Post], list[Comment]]:
        """Fetch detail pages in parallel and merge content/comment data."""
        if not posts:
            return [], []

        enriched: list[Post] = []
        comments: list[Comment] = []
        with ThreadPoolExecutor(max_workers=self.runtime.thread_workers) as executor:
            future_map = {executor.submit(self.fetch_post_detail, post): post for post in posts}
            for future in tqdm(as_completed(future_map), total=len(future_map), desc="post details"):
                original = future_map[future]
                try:
                    post, post_comments = future.result()
                    enriched.append(post)
                    if self.runtime.crawl_comment:
                        comments.extend(post_comments)
                except Exception as exc:
                    self.logger.exception("Detail failed link=%s error=%s", original.link, exc)
                    enriched.append(original)
        enriched.sort(key=lambda item: int(item.number) if item.number.isdigit() else 0, reverse=True)
        return enriched, comments

    def fetch_post_detail(self, post: Post) -> tuple[Post, list[Comment]]:
        """Fetch and parse one post detail page."""
        html = self.fetch_text(post.link)
        if self.runtime.save_html:
            self.save_html(post, html)
        updated, comments = parse_post_detail(html, post)
        if self.runtime.crawl_comment and updated.comment_count > 0 and not comments:
            comments = self.fetch_ajax_comments(updated, html)
        return updated, comments

    def fetch_ajax_comments(self, post: Post, html: str) -> list[Comment]:
        """Fetch comments from Theqoo's AJAX comment endpoint."""
        document_srl = self.extract_document_srl(post, html)
        if not document_srl:
            return []

        comments: list[Comment] = []
        seen_pages: set[int] = set()
        next_page = 0
        while next_page not in seen_pages:
            seen_pages.add(next_page)
            payload = self.post_json(
                urljoin(self.runtime.base_url, "/index.php"),
                data={
                    "act": "dispTheqooContentCommentListTheqoo",
                    "document_srl": document_srl,
                    "cpage": next_page,
                },
                referer=post.link,
            )
            comments.extend(parse_comment_json(payload, post))

            page = self._int_from_payload(payload.get("now_comment_page"))
            next_page = page - 1 if page and page > 1 else -1
            if next_page < 1:
                break
        return merge_comments([], comments)

    def fetch_text(self, url: str) -> str:
        """Fetch text with retry and polite delay."""
        last_error: Exception | None = None
        for attempt in range(1, self.runtime.max_retry + 1):
            try:
                response = self.session.get(url, timeout=self.runtime.timeout)
                if response.status_code == 404:
                    raise requests.HTTPError("404 Not Found", response=response)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or "utf-8"
                time.sleep(self.runtime.request_delay)
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                self.logger.warning("Retry %s/%s url=%s error=%s", attempt, self.runtime.max_retry, url, exc)
                time.sleep(self.runtime.request_delay * attempt)
        raise RuntimeError(f"Request failed after retries: {url}") from last_error

    def post_json(self, url: str, data: dict[str, object], referer: str) -> dict[str, object]:
        """POST a form request and parse a JSON response with retry."""
        last_error: Exception | None = None
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
        }
        for attempt in range(1, self.runtime.max_retry + 1):
            try:
                response = self.session.post(url, data=data, headers=headers, timeout=self.runtime.timeout)
                response.raise_for_status()
                time.sleep(self.runtime.request_delay)
                payload = response.json()
                return payload if isinstance(payload, dict) else {}
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                self.logger.warning("Retry %s/%s url=%s error=%s", attempt, self.runtime.max_retry, url, exc)
                time.sleep(self.runtime.request_delay * attempt)
        raise RuntimeError(f"JSON request failed after retries: {url}") from last_error

    def save_html(self, post: Post, html: str) -> None:
        """Persist original detail HTML for auditing."""
        board_dir = self.runtime.html_dir / post.board
        ensure_directories(board_dir)
        (board_dir / f"{post.number}.html").write_text(html, encoding="utf-8")

    def board_url(self, board: str, page: int) -> str:
        """Build a board-list URL."""
        return urljoin(self.runtime.base_url, f"/{board}?page={page}")

    def extract_document_srl(self, post: Post, html: str) -> str:
        """Extract Theqoo document_srl from detail HTML or URL."""
        match = re.search(r"loadReply\((\d+),", html)
        if match:
            return match.group(1)
        match = re.search(r"/(\d+)(?:[?#].*)?$", post.link)
        return match.group(1) if match else ""

    def _int_from_payload(self, value: object) -> int:
        """Safely coerce numeric JSON values."""
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return 0


def build_runtime_config(
    boards: list[str] | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
    crawl_content: bool | None = None,
    crawl_comment: bool | None = None,
    save_html: bool | None = None,
) -> RuntimeConfig:
    """Merge CLI arguments with config.py defaults."""
    effective_crawl_content = config.CRAWL_CONTENT if crawl_content is None else crawl_content
    effective_crawl_comment = config.CRAWL_COMMENT if crawl_comment is None else crawl_comment
    if not effective_crawl_content:
        effective_crawl_comment = False

    return RuntimeConfig(
        boards=boards or config.BOARDS,
        start_page=start_page or config.START_PAGE,
        end_page=end_page or config.END_PAGE,
        crawl_content=effective_crawl_content,
        crawl_comment=effective_crawl_comment,
        save_html=config.SAVE_HTML if save_html is None else save_html,
        request_delay=config.REQUEST_DELAY,
        max_retry=config.MAX_RETRY,
        thread_workers=config.THREAD_WORKERS,
        timeout=config.TIMEOUT,
        base_url=config.BASE_URL,
        headers=config.HEADERS,
        output_dir=config.OUTPUT_DIR,
        log_dir=config.LOG_DIR,
        html_dir=config.HTML_DIR,
    )
