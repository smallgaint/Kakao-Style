"""HTML parsing functions for Theqoo pages."""

from __future__ import annotations

from copy import copy
from typing import Any, Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from models import Comment, Post
from utils import clean_text, normalize_date, parse_int


def parse_board_posts(html: str, board: str, base_url: str) -> list[Post]:
    """Parse post metadata from a board list page."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.theqoo_board_table")
    if table is None:
        return []

    posts: list[Post] = []
    for row in table.select("tbody.hide_notice > tr"):
        if _is_non_post_row(row):
            continue

        number = clean_text(_cell_text(row, "td.no"))
        title_cell = row.select_one("td.title")
        title_link = _first_content_link(title_cell)
        if not number or title_link is None:
            continue

        posts.append(
            Post(
                number=number,
                category=clean_text(_cell_text(row, "td.cate")),
                title=clean_text(title_link.get_text(" ", strip=True)),
                has_image=title_cell.select_one("i.fa-images, i.fas.fa-images") is not None
                if title_cell
                else False,
                comment_count=parse_int(_cell_text(row, "a.replyNum")),
                date=normalize_date(_cell_text(row, "td.time")),
                view_count=parse_int(_cell_text(row, "td.m_no")),
                link=urljoin(base_url, title_link.get("href", "")),
                board=board,
            )
        )
    return posts


def parse_post_detail(html: str, post: Post) -> tuple[Post, list[Comment]]:
    """Parse content, image count, and comments from a detail page."""
    soup = BeautifulSoup(html, "lxml")
    updated = copy(post)

    content_node = soup.select_one("article div.rhymix_content.xe_content")
    if content_node is not None:
        updated.content = extract_text_with_breaks(content_node)
        updated.image_count = len(content_node.select("img"))

    comments = list(parse_comments(soup, updated))
    return updated, comments


def parse_comments(soup: BeautifulSoup, post: Post) -> Iterable[Comment]:
    """Parse comments from a detail page if they are present in HTML."""
    comment_list = soup.select_one("ul.fdb_lst_ul")
    if comment_list is None:
        return []

    comments: list[Comment] = []
    for item in comment_list.select("li.fdb_itm"):
        content_node = item.select_one("div.xe_content")
        if content_node is None:
            continue
        date_node = item.select_one("div.meta, span.date, time")
        comments.append(
            Comment(
                post_number=post.number,
                post_link=post.link,
                board=post.board,
                content=extract_text_with_breaks(content_node),
                date=normalize_date(date_node.get_text(" ", strip=True) if date_node else ""),
            )
        )
    return comments


def parse_comment_json(payload: dict[str, Any], post: Post) -> list[Comment]:
    """Parse comment_list returned by Theqoo's AJAX comment endpoint."""
    comment_list = payload.get("comment_list")
    if not isinstance(comment_list, (list, dict)):
        return []

    raw_items = comment_list.values() if isinstance(comment_list, dict) else comment_list
    comments: list[Comment] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        content = _comment_content(item)
        if not content:
            continue
        comments.append(
            Comment(
                post_number=post.number,
                post_link=post.link,
                board=post.board,
                content=content,
                date=_comment_date(item),
            )
        )
    return comments


def extract_text_with_breaks(node: Tag) -> str:
    """Extract visible text while preserving common block-level breaks."""
    html = str(node)
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.select("script, style, ins"):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "tr"]):
        if block.contents and block.contents[-1] != "\n":
            block.append("\n")
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def extract_text_from_html(value: str) -> str:
    """Extract plain text from a small HTML fragment."""
    soup = BeautifulSoup(value or "", "lxml")
    body = soup.body or soup
    return extract_text_with_breaks(body)


def _is_non_post_row(row: Tag) -> bool:
    """Return True for notice expanders and malformed table rows."""
    classes = set(row.get("class", []))
    return bool(classes.intersection({"notice", "notice_expand"})) or row.select_one("td[colspan]") is not None


def _cell_text(row: Tag, selector: str) -> str:
    """Safely extract text from a row selector."""
    node = row.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""


def _first_content_link(title_cell: Tag | None) -> Tag | None:
    """Find the post link, ignoring reply-count anchors."""
    if title_cell is None:
        return None
    for link in title_cell.select("a[href]"):
        classes = set(link.get("class", []))
        if "replyNum" not in classes:
            return link
    return None


def _comment_content(item: dict[str, Any]) -> str:
    """Read comment content from known Rhymix/XE response keys."""
    for key in ("content", "ct", "comment", "text", "comment_content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return extract_text_from_html(value)
    return ""


def _comment_date(item: dict[str, Any]) -> str:
    """Normalize comment date from response fields."""
    for key in ("regdate", "rd", "date", "created_at"):
        value = item.get(key)
        if not value:
            continue
        text = str(value)
        if len(text) >= 8 and text[:8].isdigit():
            return f"{text[2:4]}.{text[4:6]}.{text[6:8]}"
        return normalize_date(text)
    return ""
