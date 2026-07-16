"""Parsers for Pann search result, post, and comment HTML."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from models import Comment, Post


def parse_search_results(html: str, keyword: str, base_url: str) -> list[Post]:
    """Parse only the actual Pann search-result rows (``ul.s_list > li``)."""
    soup = BeautifulSoup(html, "lxml")
    posts: list[Post] = []
    for item in soup.select("ul.s_list > li"):
        title_link = item.select_one("a.subject[href]")
        date_node = item.select_one(".info .date")
        if title_link is None or date_node is None:
            continue

        url = urljoin(base_url, str(title_link["href"]))
        post_id = _post_id(url)
        created_at = parse_datetime(_text(date_node))
        if not post_id or created_at is None:
            continue

        posts.append(
            Post(
                post_id=post_id,
                matched_keywords=keyword,
                title=clean_text(title_link.get_text(" ", strip=True)),
                comment_count=parse_int(_text(item.select_one(".reple-num"))),
                board=clean_text(_text(item.select_one(".info .part"))),
                author=clean_text(_text(item.select_one(".info .writer"))),
                created_at=created_at,
                view_count=0,
                url=url,
            )
        )
    return posts


def parse_post_detail(html: str) -> tuple[str, int]:
    """Return visible post body text and view count from a detail page."""
    soup = BeautifulSoup(html, "lxml")
    content_node = soup.select_one("#contentArea")
    content = extract_text_with_breaks(content_node) if content_node else ""
    view_count = parse_int(_text(soup.select_one(".post-tit-info .info .count, .info .count")))
    return content, view_count


def parse_comments(html: str, post_id: str, post_url: str) -> list[Comment]:
    """Parse regular comments returned by either article or reply-load HTML."""
    soup = BeautifulSoup(html, "lxml")
    comments: list[Comment] = []
    for item in soup.select(".cmt_list > dl.cmt_item"):
        # Current Pann markup uses ``usertxt``; accept the documented/legacy
        # ``usertext`` spelling as well.
        content_node = item.select_one(".usertxt, .usertext")
        if content_node is None:
            continue
        content = extract_text_with_breaks(content_node)
        if not content:
            continue
        comments.append(
            Comment(
                post_id=post_id,
                post_url=post_url,
                author=clean_text(_text(item.select_one("dt .nameui"))),
                created_at=clean_text(_text(item.select_one("dt i"))),
                content=content,
            )
        )
    return comments


def parse_last_comment_page(html: str) -> int:
    """Return the final regular-comment page advertised by the response."""
    soup = BeautifulSoup(html, "lxml")
    pagination = soup.select_one(".paginate-reple")
    if pagination is None:
        return 1
    values = [int(value) for value in re.findall(r"\d+", pagination.get_text(" ", strip=True))]
    values.extend(int(value) for value in re.findall(r"loadReply\s*\(\s*(\d+)", str(pagination)))
    return max(values, default=1)


def parse_datetime(value: str) -> datetime | None:
    text = clean_text(value)
    for pattern in ("%y.%m.%d %H:%M", "%Y.%m.%d %H:%M", "%y.%m.%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            pass
    return None


def extract_text_with_breaks(node: Tag) -> str:
    """Extract text while retaining paragraph and line-break boundaries."""
    fragment = BeautifulSoup(str(node), "lxml")
    for tag in fragment.select("script, style, noscript"):
        tag.decompose()
    for br in fragment.select("br"):
        br.replace_with("\n")
    for block in fragment.select("p, div, li, dd"):
        block.append("\n")
    lines = [clean_text(line) for line in fragment.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_int(value: str | None) -> int:
    digits = re.sub(r"\D", "", value or "")
    return int(digits) if digits else 0


def _text(node: Tag | None) -> str:
    return node.get_text(" ", strip=True) if node else ""


def _post_id(url: str) -> str:
    candidate = urlparse(url).path.rstrip("/").split("/")[-1]
    return candidate if candidate.isdigit() else ""
