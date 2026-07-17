"""CLI entry point for the Daum Cafe date-bounded search crawler."""

from __future__ import annotations

import argparse
import time

import config
from crawler import DaumCafeCrawler, build_runtime_config
from utils import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl Daum Cafe all-board search results by date range.")
    parser.add_argument("--keyword", action="append", dest="single_keywords", help="Search keyword; may be repeated")
    parser.add_argument("--keywords", nargs="+", help="Replace CONFIG search keywords")
    parser.add_argument("--start-date", help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Inclusive end date (YYYY-MM-DD)")
    parser.add_argument("--crawl-details", dest="crawl_details", action="store_true", default=None)
    parser.add_argument("--no-crawl-details", dest="crawl_details", action="store_false")
    parser.add_argument("--headed", action="store_true", help="Show the browser for manual login")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    keywords = args.keywords or args.single_keywords
    if args.keywords and args.single_keywords:
        keywords = [*args.keywords, *args.single_keywords]
    runtime = build_runtime_config(
        keywords=keywords,
        start_date=args.start_date,
        end_date=args.end_date,
        crawl_details=args.crawl_details,
        headless=False if args.headed else None,
    )
    logger = setup_logging(config.LOG_DIR)
    crawler = DaumCafeCrawler(runtime, logger)
    started = time.perf_counter()
    try:
        crawler.start_browser()
        crawler.login()
        stat = crawler.crawl_search()
    finally:
        crawler.close_browser()
    elapsed = time.perf_counter() - started
    print(
        f"Crawl summary: pages={stat.pages}, new_posts={stat.posts}, "
        f"comments={stat.comments}, errors={stat.errors}, elapsed={elapsed:.2f}s"
    )


if __name__ == "__main__":
    main()
