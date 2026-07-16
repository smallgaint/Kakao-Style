"""Regression tests based on the supplied saved Pann HTML examples."""

from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

CRAWLER_DIR = Path(__file__).resolve().parents[1]
PANN_DIR = CRAWLER_DIR.parent
sys.path.insert(0, str(CRAWLER_DIR))

from crawler import is_in_date_range
from parser import parse_comments, parse_last_comment_page, parse_post_detail, parse_search_results
from utils import load_posts, merge_posts, write_posts


class PannParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.search_html = (PANN_DIR / "pannate_search_talk.html").read_text(encoding="utf-8")
        cls.detail_html = (PANN_DIR / "pannate_beauty_content_1.html").read_text(encoding="utf-8")
        cls.posts = parse_search_results(cls.search_html, "테스트", "https://pann.nate.com")

    def test_search_rows_and_metadata(self) -> None:
        self.assertEqual(len(self.posts), 10)
        first = self.posts[0]
        self.assertEqual(first.post_id, "375519734")
        self.assertEqual(first.url, "https://pann.nate.com/talk/375519734")
        self.assertTrue(first.title)
        self.assertEqual(first.board, "30대 이야기")
        self.assertEqual(first.author, "GravityNgc")
        self.assertEqual(first.comment_count, 0)

    def test_detail_and_comments(self) -> None:
        content, views = parse_post_detail(self.detail_html)
        comments = parse_comments(self.detail_html, "375508338", "https://pann.nate.com/talk/375508338")
        self.assertEqual(views, 55)
        self.assertIn("팔자주름", content)
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].author, "ㅇㅇ")
        self.assertEqual(comments[0].created_at, "2026.07.09 19:02")
        self.assertTrue(comments[0].content)

    def test_date_range_boundaries(self) -> None:
        self.assertTrue(is_in_date_range(date(2026, 7, 10), date(2026, 7, 10), date(2026, 7, 16)))
        self.assertTrue(is_in_date_range(date(2026, 7, 16), date(2026, 7, 10), date(2026, 7, 16)))
        self.assertFalse(is_in_date_range(date(2026, 7, 9), date(2026, 7, 10), date(2026, 7, 16)))

    def test_comment_pagination(self) -> None:
        html = '<div class="paginate-reple"><strong>1</strong><a onclick="loadReply(2, \'\', \'W\')">2</a><a onclick="loadReply(3, \'\', \'W\')">3</a></div>'
        self.assertEqual(parse_last_comment_page(html), 3)

    def test_post_merge_and_resume(self) -> None:
        original = self.posts[0]
        updated = replace(original, matched_keywords="테스트 | 다른키워드")
        merged = merge_posts([original], [updated])
        self.assertEqual(len(merged), 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "posts.csv"
            write_posts(path, merged)
            self.assertEqual(load_posts(path), merged)


if __name__ == "__main__":
    unittest.main()
