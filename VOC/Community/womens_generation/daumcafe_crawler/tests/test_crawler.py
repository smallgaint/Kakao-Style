"""Search date-range and checkpoint behaviour."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import logging
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import crawler as crawler_module
from crawler import DaumCafeCrawler, build_runtime_config
from models import Post


def _post(number: int, raw_date: str = "26.07.10") -> Post:
    return Post(str(number), str(number), "Lp0T", "자유게시판", f"title {number}", "author", False, 0, 0, raw_date, 0, f"https://example.test/{number}")


def test_date_boundaries_are_inclusive() -> None:
    assert DaumCafeCrawler._post_date("26.07.01") == date(2026, 7, 1)
    assert DaumCafeCrawler._post_date("26.07.16") == date(2026, 7, 16)
    assert DaumCafeCrawler._post_date("invalid") is None


def test_checkpoint_saves_at_50_and_final_remainder(tmp_path, monkeypatch) -> None:
    runtime = replace(
        build_runtime_config(keywords=["test"], start_date="2026-07-01", end_date="2026-07-16", crawl_details=False),
        output_dir=tmp_path,
        log_dir=tmp_path / "logs",
        html_dir=tmp_path / "html",
        login_storage_state=tmp_path / "auth" / "state.json",
        checkpoint_size=50,
    )
    crawler = DaumCafeCrawler(runtime, logging.getLogger("test-checkpoint"))
    crawler.context = object()  # Network access is replaced below.
    crawler.fetch_search_page = lambda keyword, page: "first" if page == 1 else "last"  # type: ignore[method-assign]
    calls = {"count": 0}

    def fake_parse(html: str, base_url: str, keyword: str) -> list[Post]:
        calls["count"] += 1
        return [_post(value) for value in range(1, 52)] if calls["count"] == 1 else []

    writes = {"count": 0}
    original_write = crawler_module.write_posts

    def count_writes(path, posts):
        writes["count"] += 1
        original_write(path, posts)

    monkeypatch.setattr(crawler_module, "parse_search_results", fake_parse)
    monkeypatch.setattr(crawler_module, "write_posts", count_writes)
    stat = crawler.crawl_search()

    assert stat.posts == 51
    assert writes["count"] == 2
    assert len((tmp_path / "daumcafe_search_20260701_20260716.csv").read_text(encoding="utf-8-sig").splitlines()) == 52
