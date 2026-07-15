"""Unit tests for parser stability."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parser import extract_iframe_src, parse_post_detail
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
