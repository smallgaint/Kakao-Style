"""Newest-first Pann keyword-search crawler."""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import replace
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import requests
from tqdm import tqdm

import config
from models import Comment, CrawlStats, Post
from parser import parse_comments, parse_last_comment_page, parse_post_detail, parse_search_results
from utils import ensure_directories, load_comments, load_posts, merge_comments, merge_posts, setup_logging, write_comments, write_posts


def is_in_date_range(created_at: date, start_date: date, end_date: date) -> bool:
    """Return whether a post date belongs to the inclusive configured window."""
    return start_date <= created_at <= end_date


class PannSearchCrawler:
    def __init__(self) -> None:
        ensure_directories(config.DATA_DIR, config.HTML_DIR, config.LOG_DIR)
        self.logger = setup_logging(config.LOG_FILE)
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS)

    def crawl_all(
        self,
        keywords: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CrawlStats:
        keywords = keywords or config.KEYWORDS
        start_date = start_date or config.START_DATE
        end_date = end_date or config.END_DATE
        if start_date > end_date:
            raise ValueError("START_DATE must not be later than END_DATE")

        posts = load_posts(config.POST_OUTPUT) if config.ENABLE_RESUME else []
        comments = load_comments(config.COMMENT_OUTPUT) if config.ENABLE_RESUME else []
        posts_by_id = {post.post_id: post for post in posts}
        stats = CrawlStats()

        for keyword in keywords:
            self._crawl_keyword(keyword, start_date, end_date, posts_by_id, posts, comments, stats)
            self._save(posts, comments)

        self._save(posts, comments)
        return stats

    def _crawl_keyword(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        posts_by_id: dict[str, Post],
        posts: list[Post],
        comments: list[Comment],
        stats: CrawlStats,
    ) -> None:
        self.logger.info("Start keyword=%r date_range=%s..%s", keyword, start_date, end_date)
        for page in tqdm(range(1, config.MAX_PAGES_PER_KEYWORD + 1), desc=f"{keyword} search pages"):
            try:
                results = parse_search_results(self.get_text(self.search_url(keyword, page)), keyword, config.BASE_URL)
            except Exception:
                stats.errors += 1
                self.logger.exception("Search request failed keyword=%r page=%s", keyword, page)
                return

            if not results:
                self.logger.info("No search results keyword=%r page=%s", keyword, page)
                return
            stats.search_pages += 1
            has_old_post = False

            for post in results:
                post_date = post.created_at.date()
                if post_date < start_date:
                    has_old_post = True
                    continue
                if post_date > end_date:
                    continue

                existing = posts_by_id.get(post.post_id)
                if existing is not None:
                    updated = self._add_keyword(existing, keyword)
                    if updated != existing:
                        posts[:] = merge_posts(posts, [updated])
                        posts_by_id[post.post_id] = updated
                    continue

                try:
                    enriched, new_comments = self.enrich_post(post)
                    posts[:] = merge_posts(posts, [enriched])
                    comments[:] = merge_comments(comments, new_comments)
                    posts_by_id[enriched.post_id] = enriched
                    stats.posts += 1
                    stats.comments += len(new_comments)
                except Exception:
                    stats.errors += 1
                    self.logger.exception("Post request failed post_id=%s url=%s", post.post_id, post.url)

            if page % config.AUTO_SAVE_EVERY == 0:
                self._save(posts, comments)
            # DD is newest-first, so no later search page can return an in-range post.
            if has_old_post:
                self.logger.info("Reached START_DATE keyword=%r page=%s", keyword, page)
                return

        self.logger.warning("Reached MAX_PAGES_PER_KEYWORD keyword=%r", keyword)

    def enrich_post(self, post: Post) -> tuple[Post, list[Comment]]:
        if not config.CRAWL_CONTENT:
            return post, []
        html = self.get_text(post.url)
        if config.SAVE_HTML:
            self._save_html(post.post_id, html)
        content, view_count = parse_post_detail(html)
        enriched = replace(post, content=content, view_count=view_count)
        return enriched, self._crawl_comments(enriched, html) if config.CRAWL_COMMENT else []

    def _crawl_comments(self, post: Post, first_page_html: str) -> list[Comment]:
        comments = parse_comments(first_page_html, post.post_id, post.url)
        last_page = parse_last_comment_page(first_page_html)
        visited_pages = {1}
        page = 2
        while page <= last_page and page not in visited_pages:
            visited_pages.add(page)
            fragment = self.post_text(
                config.COMMENT_LOAD_URL,
                data={
                    "pann_id": post.post_id,
                    "reply_id": 0,
                    "rereply_id": 0,
                    "page": page,
                    "penm": "",
                    "order": "W",
                },
                referer=post.url,
            )
            comments = merge_comments(comments, parse_comments(fragment, post.post_id, post.url))
            last_page = max(last_page, parse_last_comment_page(fragment))
            page += 1
        return comments

    def get_text(self, url: str) -> str:
        return self._request_text("GET", url)

    def post_text(self, url: str, data: dict[str, object], referer: str) -> str:
        return self._request_text("POST", url, data=data, headers={"Referer": referer, "X-Requested-With": "XMLHttpRequest"})

    def _request_text(self, method: str, url: str, **kwargs: object) -> str:
        last_error: requests.RequestException | None = None
        for attempt in range(1, config.MAX_RETRY + 1):
            try:
                response = self.session.request(method, url, timeout=config.TIMEOUT, **kwargs)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or "utf-8"
                self._sleep()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                self.logger.warning("Request retry=%s/%s method=%s url=%s error=%s", attempt, config.MAX_RETRY, method, url, exc)
                time.sleep(config.REQUEST_DELAY * attempt)
        raise RuntimeError(f"Request failed after {config.MAX_RETRY} attempts: {url}") from last_error

    @staticmethod
    def search_url(keyword: str, page: int) -> str:
        return f"{config.SEARCH_URL}?{urlencode({'q': keyword, 'sort': config.SORT, 'page': page})}"

    @staticmethod
    def _add_keyword(post: Post, keyword: str) -> Post:
        keywords = [value for value in post.matched_keywords.split(" | ") if value]
        return post if keyword in keywords else replace(post, matched_keywords=" | ".join([*keywords, keyword]))

    @staticmethod
    def _save(posts: list[Post], comments: list[Comment]) -> None:
        write_posts(config.POST_OUTPUT, posts)
        if config.CRAWL_COMMENT:
            write_comments(config.COMMENT_OUTPUT, comments)

    @staticmethod
    def _save_html(post_id: str, html: str) -> None:
        (Path(config.HTML_DIR) / f"{post_id}.html").write_text(html, encoding="utf-8")

    @staticmethod
    def _sleep() -> None:
        time.sleep(config.REQUEST_DELAY + random.uniform(0, config.REQUEST_DELAY_RANDOM))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect newest-first Pann keyword search results.")
    parser.add_argument("--keywords", nargs="+", help="Override config.KEYWORDS")
    parser.add_argument("--start-date", type=date.fromisoformat, help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=date.fromisoformat, help="Inclusive end date (YYYY-MM-DD)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = PannSearchCrawler().crawl_all(args.keywords, args.start_date, args.end_date)
    print(f"Crawl summary: search_pages={stats.search_pages}, posts={stats.posts}, comments={stats.comments}, errors={stats.errors}")


if __name__ == "__main__":
    main()
