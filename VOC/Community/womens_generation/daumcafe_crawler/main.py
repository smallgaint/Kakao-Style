"""CLI entry point for the Daum Cafe crawler."""

from __future__ import annotations

import argparse
import time

import config
from crawler import DaumCafeCrawler, build_runtime_config
from utils import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Crawl Daum Cafe boards without Selenium.")
    parser.add_argument("--boards", nargs="+", help="Board ids such as ReHf ReHw")
    parser.add_argument("--start", type=int, help="Start page")
    parser.add_argument("--end", type=int, help="End page")
    parser.add_argument("--crawl-content", dest="crawl_content", action="store_true", default=None)
    parser.add_argument("--no-crawl-content", dest="crawl_content", action="store_false")
    parser.add_argument("--crawl-comment", dest="crawl_comment", action="store_true", default=None)
    parser.add_argument("--no-crawl-comment", dest="crawl_comment", action="store_false")
    parser.add_argument("--save-html", dest="save_html", action="store_true", default=None)
    parser.add_argument("--no-save-html", dest="save_html", action="store_false")
    parser.add_argument("--only-new-posts", dest="only_new_posts", action="store_true", default=None)
    parser.add_argument("--all-posts", dest="only_new_posts", action="store_false")
    return parser.parse_args()


def main() -> None:
    """Run the crawler and print crawl statistics."""
    args = parse_args()
    runtime = build_runtime_config(
        boards=args.boards,
        start_page=args.start,
        end_page=args.end,
        crawl_content=args.crawl_content,
        crawl_comment=args.crawl_comment,
        save_html=args.save_html,
        only_new_posts=args.only_new_posts,
    )
    logger = setup_logging(config.LOG_DIR)
    started = time.perf_counter()
    stats = DaumCafeCrawler(runtime, logger).crawl_all()
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
