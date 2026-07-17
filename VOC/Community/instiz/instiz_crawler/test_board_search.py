"""게시판별 검색 HTML fixture 검증."""

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crawler import InstizCrawler
from parser import InstizParser


class BoardSearchParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = Path(__file__).resolve().parent.parent / "instiz_life_search.html"
        cls.posts = InstizParser.parse_board_search_results(fixture.read_text(encoding="utf-8"), "name")

    def test_fixture_parses_only_normal_list_rows(self):
        self.assertGreater(len(self.posts), 0)
        post_id, title, _, url, comments, views, likes, raw_date, _ = self.posts[0]
        self.assertEqual(post_id, 66283767)
        self.assertEqual(url, "https://www.instiz.net/name/66283767")
        self.assertEqual(title, "다들 싼 옷도 드라이클리닝 맡겨?")
        self.assertEqual(comments, 8)
        self.assertEqual(views, 25)
        self.assertEqual(likes, 0)
        self.assertEqual(raw_date, "04.29 16:41")

    def test_search_url_with_and_without_category(self):
        crawler = InstizCrawler()
        self.assertEqual(
            crawler.build_board_search_url("name", 1, "지그재그", 1),
            "https://www.instiz.net/name?page=1&k=%EC%A7%80%EA%B7%B8%EC%9E%AC%EA%B7%B8&stype=9&category=1",
        )
        self.assertEqual(
            crawler.build_board_search_url("name_beauty", None, "지그재그", 2),
            "https://www.instiz.net/name_beauty?page=2&k=%EC%A7%80%EA%B7%B8%EC%9E%AC%EA%B7%B8&stype=9",
        )

    def test_year_rollover_uses_descending_search_order(self):
        first = InstizCrawler._resolve_search_datetime("01.02 12:00", None)
        second = InstizCrawler._resolve_search_datetime("12.31 23:00", first)
        self.assertEqual(second.year, first.year - 1)
        self.assertLess(second, first)


if __name__ == "__main__":
    unittest.main()
