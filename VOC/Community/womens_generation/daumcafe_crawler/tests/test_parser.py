"""Unit tests for parser stability."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parser import extract_iframe_src, has_next_search_page, parse_post_detail, parse_search_results
from models import Post
from utils import normalize_date


def test_normalize_date() -> None:
    """Dates are normalized to YY.MM.DD."""
    assert normalize_date("26.07.12") == "26.07.12"
    assert normalize_date("07.12").endswith(".07.12")


def test_extract_iframe_src() -> None:
    """Main cafe iframe is extracted from the outer page."""
    html = '<iframe id="down" src="/_c21_/bbs_list?grpid=1IHuH&fldid=ReHf"></iframe>'
    assert extract_iframe_src(html, "https://cafe.daum.net").endswith("fldid=ReHf")


def test_parse_post_detail_sample() -> None:
    """Detail parser handles Daum Cafe user_contents."""
    sample = ROOT.parent / "womens_generation_ReHf_content_1_files" / "bbs_list.html"
    if not sample.exists():
        return
    post = Post("5691867", "5691867", "ReHf", "", "sample", "", False, 0, 0, "", 0, "https://cafe.daum.net/subdued20club/ReHf/5691867")
    parsed, _ = parse_post_detail(sample.read_text(encoding="utf-8"), post)
    assert parsed.image_count >= 1


def test_parse_search_fixture() -> None:
    """Search info and preview rows are combined into one post."""
    fixture = ROOT.parent / "womens_generation_search_files" / "home.html"
    posts = parse_search_results(fixture.read_text(encoding="utf-8"), "https://cafe.daum.net", "지그재그")
    assert len(posts) == 20
    first = posts[0]
    assert first.number == "11499774"
    assert first.post_id == "11499774"
    assert first.board == "VN83"
    assert first.category == "금전거래전용게시판"
    assert first.has_image is True
    assert first.author == "001122"
    assert first.view_count == 12
    assert first.preview
    assert first.search_keywords == "지그재그"


def test_permission_notice_keeps_search_preview() -> None:
    post = Post("1", "1", "test", "", "title", "author", False, 0, 0, "26.07.16", 0, "https://example.test", preview="preview")
    html = '<div class="sub_title line_title_sub">**자유게시판 게시판 권한 안내</div><div id="user_contents">hidden</div>'
    parsed, comments = parse_post_detail(html, post)
    assert parsed.preview == "preview"
    assert parsed.content == ""
    assert comments == []


def test_search_pager_detects_last_page() -> None:
    assert has_next_search_page('<span class="num_next"><a href="javascript:goPage(2)">다음</a></span>')
    assert not has_next_search_page('<span class="num_next">다음</span>')
