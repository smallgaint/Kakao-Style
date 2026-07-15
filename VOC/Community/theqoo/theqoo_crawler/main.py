"""CLI entry point for the Theqoo crawler."""

from __future__ import annotations

import argparse
import time

import config
from crawler import TheqooCrawler, build_runtime_config
from utils import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line options that override config.py."""
    parser = argparse.ArgumentParser(description="Crawl Theqoo board posts with requests and BeautifulSoup.")
    parser.add_argument("--boards", nargs="+", help="Board names such as beauty fashion")
    parser.add_argument("--start", type=int, help="Start page")
    parser.add_argument("--end", type=int, help="End page")
    parser.add_argument("--crawl-content", dest="crawl_content", action="store_true", default=None)
    parser.add_argument("--no-crawl-content", dest="crawl_content", action="store_false")
    parser.add_argument("--crawl-comment", dest="crawl_comment", action="store_true", default=None)
    parser.add_argument("--no-crawl-comment", dest="crawl_comment", action="store_false")
    parser.add_argument("--save-html", dest="save_html", action="store_true", default=None)
    parser.add_argument("--keywords", nargs="+", help="Keywords to filter posts by title")
    parser.add_argument("--no-save-html", dest="save_html", action="store_false")
    return parser.parse_args()


def main() -> None:
    """Run the crawler and print summary statistics."""
    args = parse_args()
    runtime = build_runtime_config(
        boards=args.boards,
        start_page=args.start,
        end_page=args.end,
        crawl_content=args.crawl_content,
        crawl_comment=args.crawl_comment,
        save_html=args.save_html,
        keywords=args.keywords,
    )
    logger = setup_logging(config.LOG_DIR)
    started = time.perf_counter()

    crawler = TheqooCrawler(runtime, logger)
    stats = crawler.crawl_all()

    elapsed = time.perf_counter() - started
    total_posts = sum(stat.posts for stat in stats)
    total_comments = sum(stat.comments for stat in stats)
    speed = total_posts / elapsed if elapsed else 0.0

    print("\nCrawl summary")
    for stat in stats:
        print(
            f"- {stat.board}: pages={stat.pages}, posts={stat.posts}, "
            f"comments={stat.comments}, errors={stat.errors}"
        )
    print(f"elapsed={elapsed:.2f}s, average_speed={speed:.2f} posts/sec, total_comments={total_comments}")


if __name__ == "__main__":
    main()
