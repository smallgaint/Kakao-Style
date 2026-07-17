"""Daum Cafe HTML parsers.

All CSS selectors live in SELECTORS. If Daum changes markup, update this
dictionary first; crawler.py and the rest of the program do not contain
site-specific selector strings.
"""

from __future__ import annotations

import re
from copy import copy
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from models import Comment, Post
from utils import clean_text, normalize_date, parse_int


SELECTORS: dict[str, Any] = {
    "iframe": {
        "main": ["iframe#down", "iframe[name='down']", "iframe[title*='카페'][src]"],
        "ignore_src_contains": ["google", "ads", "about:blank"],
    },
    "board": {
        "article_scripts": ["script"],
        "rows": [
            "table.bbsList tbody tr",
            "table.list_bbs tbody tr",
            "table.article-board tbody tr",
            "#primaryContent table tbody tr",
        ],
        "title_link": ["td.subject a[href]", "a.txt_item[href]", "a.link_item[href]", "a[href*='bbs_read']"],
        "category": ["td.category", "td.head", ".txt_category", ".head_cont"],
        "author": ["td.nick a", "td.nick", "td.writer a", "td.writer", ".txt_writer", ".nickname"],
        "date": ["td.date", "td.regdate", ".txt_date", ".date"],
        "views": ["td.count", "td.view", "td.hit", ".txt_view", ".view"],
        "number": ["td.num", "td.no", ".num"],
        "comment_count": ["a.txt_point", ".comment", ".reply", ".txt_cmt"],
        "image_marker": ["img[alt*='첨부']", "img.icon_pic", ".ico_attach", ".ico_photo", "img[src*='ico_pic']"],
    },
    "search": {
        "rows": ["tr.list_row_info"],
        "number": ["td.search_num"],
        "title": ["td.searchpreview_subject > a[href]"],
        "comment_count": ["td.searchpreview_subject a.txt_point.num.b"],
        "image_marker": ["td.searchpreview_subject img.icon_file_photo"],
        "author": ["td.search_nick a", "td.search_nick span", "td.search_nick"],
        "date": ["td.date"],
        "views": ["td.search_count"],
        "preview": ["td.searchpreview_con > a.txt_sub", "td.searchpreview_con td.content > a.txt_sub"],
        "board": ["span.p11.txt_sub.bloc a"],
    },
    "detail": {
        "content": ["#user_contents", "xmp#template_xmp", "div#article", ".article_view", ".bbs_contents", ".content-article"],
        "title": ["meta[property='og:title']", "h3.tit_subject", ".tit_subject", ".article_subject"],
        "author": [".cover_info .txt_name", ".info_author .txt_name", ".writer", ".nickname"],
        "date": [".cover_info .txt_date", ".date", ".regdate"],
        "views": [".num_view", ".view_count", ".txt_view"],
    },
    "comments": {
        "items": ["#comment-list li", ".list_comment li", "li.comment_item", ".comment_item"],
        "number": ["[data-comment-id]", "[id*='comment']", ".num"],
        "author": [".txt_name", ".nickname", ".writer"],
        "date": [".txt_date", ".date", ".regdate"],
        "content": [".original_comment", ".desc_comment", ".comment_contents", ".txt_comment"],
    },
}


def extract_iframe_src(html: str, base_url: str) -> str:
    """Extract the real Daum Cafe iframe URL from an outer page."""
    soup = BeautifulSoup(html, "lxml")
    ignored = SELECTORS["iframe"]["ignore_src_contains"]
    for selector in SELECTORS["iframe"]["main"]:
        for iframe in soup.select(selector):
            src = iframe.get("src", "")
            if not src or any(token in src.lower() for token in ignored):
                continue
            return urljoin(base_url, src)
    return ""


def parse_board_posts(html: str, board: str, base_url: str) -> list[Post]:
    """Parse a Daum Cafe board iframe page."""
    soup = BeautifulSoup(html, "lxml")
    script_posts = parse_script_articles(html, board, base_url)
    if script_posts:
        return script_posts

    posts: list[Post] = []
    for row in _select_all(soup, "board", "rows"):
        if not isinstance(row, Tag):
            continue
        title_link = _first(row, "board", "title_link")
        if title_link is None:
            continue
        href = title_link.get("href", "")
        if "bbs_read" not in href and f"/{board}/" not in href:
            continue
        link = urljoin(base_url, href)
        post_id = extract_post_id(link)
        number = _text(row, "board", "number") or post_id
        title = clean_text(title_link.get_text(" ", strip=True))
        if not title:
            continue
        posts.append(
            Post(
                number=number,
                post_id=post_id,
                board=board,
                category=_text(row, "board", "category"),
                title=title,
                author=_text(row, "board", "author"),
                has_image=_first(row, "board", "image_marker") is not None,
                image_count=0,
                comment_count=parse_int(_text(row, "board", "comment_count")),
                date=normalize_date(_text(row, "board", "date")),
                view_count=parse_int(_text(row, "board", "views")),
                link=link,
            )
        )
    return posts


def parse_search_results(html: str, base_url: str, keyword: str) -> list[Post]:
    """Parse one Daum Cafe all-board search-result page.

    Every result consists of an information row followed by its preview row.
    The preview is retained independently from detail content so it remains
    available when the article is permission-restricted.
    """
    soup = BeautifulSoup(html, "lxml")
    posts: list[Post] = []
    for row in _select_all(soup, "search", "rows"):
        title_link = _first(row, "search", "title")
        if title_link is None:
            continue
        link = urljoin(base_url, title_link.get("href", ""))
        post_id = extract_post_id(link)
        number = _text(row, "search", "number") or post_id
        if not number or not link:
            continue
        preview_row = row.find_next_sibling("tr", class_="list_row_search_feed")
        preview = _text(preview_row, "search", "preview") if isinstance(preview_row, Tag) else ""
        board = _search_board_id(link)
        board_name = _text(preview_row, "search", "board") if isinstance(preview_row, Tag) else ""
        posts.append(
            Post(
                number=number,
                post_id=post_id or number,
                board=board,
                category=board_name,
                title=clean_text(title_link.get_text(" ", strip=True)),
                author=_text(row, "search", "author"),
                has_image=_first(row, "search", "image_marker") is not None,
                image_count=0,
                comment_count=parse_int(_text(row, "search", "comment_count")),
                date=normalize_date(_text(row, "search", "date")),
                view_count=parse_int(_text(row, "search", "views")),
                link=link,
                preview=preview,
                search_keywords=keyword,
            )
        )
    return posts


def parse_script_articles(html: str, board: str, base_url: str) -> list[Post]:
    """Parse modern Daum Cafe board pages rendered from articles.push data."""
    blocks = re.findall(r"articles\.push\(\s*\{(.*?)\}\s*\);", html, flags=re.DOTALL)
    posts: list[Post] = []
    for block in blocks:
        post_id = _js_string(block, "dataid")
        fldid = _js_string(block, "fldid") or board
        title = _js_string(block, "title")
        if not post_id or not title or (board and fldid != board):
            continue
        contentval = _js_string(block, "bbsdepth")
        link = build_read_url(base_url, _js_string(block, "grpid"), fldid, post_id, contentval)
        posts.append(
            Post(
                number=post_id,
                post_id=post_id,
                board=fldid,
                category=_js_string(block, "headCont"),
                title=title,
                author=_js_string(block, "author"),
                has_image=_js_bool(block, "hasImage"),
                image_count=0,
                comment_count=_js_int(block, "commentCnt"),
                date=normalize_date(_js_string(block, "created")),
                view_count=_js_int(block, "viewCnt"),
                link=link,
            )
        )
    return posts


def build_read_url(base_url: str, grpid: str, board: str, post_id: str, contentval: str) -> str:
    """Build a Daum Cafe iframe article URL from script article data."""
    query = {
        "grpid": grpid,
        "fldid": board,
        "contentval": contentval,
        "datanum": post_id,
        "page": "1",
    }
    return f"{base_url}/_c21_/bbs_read?{urlencode({k: v for k, v in query.items() if v})}"


def parse_post_detail(html: str, post: Post) -> tuple[Post, list[Comment]]:
    """Parse article content, image count, and inline comments."""
    soup = BeautifulSoup(html, "lxml")
    updated = copy(post)
    if is_access_denied(soup):
        return updated, []
    content_node = _first_nonempty(soup, "detail", "content")
    if content_node is not None:
        updated.content = extract_text_with_breaks(content_node)
        updated.image_count = len(content_node.select("img"))
        updated.has_image = updated.has_image or updated.image_count > 0
    updated.author = updated.author or _text(soup, "detail", "author") or _script_value(html, "BBSNICKNAME")
    updated.date = updated.date or normalize_date(_text(soup, "detail", "date") or _script_value(html, "PLAIN_REGDT"))
    updated.view_count = updated.view_count or parse_int(_text(soup, "detail", "views") or _script_value(html, "VIEWCOUNT"))
    return updated, parse_comments(soup, updated)


def is_access_denied(soup: BeautifulSoup) -> bool:
    """Return whether Daum displayed its board-permission guidance."""
    title = soup.select_one(".sub_title.line_title_sub")
    return bool(title and "게시판 권한 안내" in clean_text(title.get_text(" ", strip=True)))


def parse_comments(soup: BeautifulSoup, post: Post) -> list[Comment]:
    """Parse comments rendered in the detail iframe."""
    comments: list[Comment] = []
    for item in _select_all(soup, "comments", "items"):
        if not isinstance(item, Tag):
            continue
        content_node = _first(item, "comments", "content")
        content = extract_text_with_breaks(content_node) if content_node else ""
        if not content:
            continue
        comments.append(
            Comment(
                post_number=post.number,
                post_link=post.link,
                comment_number=_comment_number(item),
                author=_text(item, "comments", "author"),
                date=normalize_date(_text(item, "comments", "date")),
                content=content,
            )
        )
    return comments


def extract_post_id(url: str) -> str:
    """Extract datanum or path post id from a Daum Cafe URL."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("datanum", "dataid"):
        if query.get(key):
            return query[key][0]
    match = re.search(r"/(\d+)(?:[/?#].*)?$", parsed.path)
    return match.group(1) if match else ""


def extract_contentval(url: str) -> str:
    """Extract Daum Cafe contentval from a URL if present."""
    return parse_qs(urlparse(url).query).get("contentval", [""])[0]


def _search_board_id(url: str) -> str:
    """Extract the board id carried by a search-result article link."""
    return parse_qs(urlparse(url).query).get("fldid", [""])[0]


def extract_text_with_breaks(node: Tag) -> str:
    """Extract visible text while preserving common line breaks."""
    soup = BeautifulSoup(str(node), "lxml")
    for tag in soup.select("script, style, ins"):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "tr"]):
        if block.contents and block.contents[-1] != "\n":
            block.append("\n")
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def validate_selectors(html: str) -> dict[str, bool]:
    """Return basic selector health for logging and tests."""
    soup = BeautifulSoup(html, "lxml")
    return {
        "board_rows": bool(_select_all(soup, "board", "rows")) or bool(parse_script_articles(html, "", "")),
        "detail_content": _first(soup, "detail", "content") is not None,
        "iframe": bool(extract_iframe_src(html, "https://cafe.daum.net")),
    }


def _select_all(root: BeautifulSoup | Tag, group: str, name: str) -> list[Tag]:
    """Select nodes using selector alternatives."""
    for selector in SELECTORS[group][name]:
        nodes = root.select(selector)
        if nodes:
            return nodes
    return []


def _first(root: BeautifulSoup | Tag, group: str, name: str) -> Tag | None:
    """Return the first matching node for selector alternatives."""
    nodes = _select_all(root, group, name)
    return nodes[0] if nodes else None


def _first_nonempty(root: BeautifulSoup | Tag, group: str, name: str) -> Tag | None:
    """Return the first matching node that contains text or images."""
    for selector in SELECTORS[group][name]:
        for node in root.select(selector):
            if clean_text(node.get_text(" ", strip=True)) or node.select_one("img"):
                return node
    return None


def _text(root: BeautifulSoup | Tag, group: str, name: str) -> str:
    """Return text from the first matching selector."""
    node = _first(root, group, name)
    if node is None:
        return ""
    if node.name == "meta":
        return clean_text(node.get("content", ""))
    return clean_text(node.get_text(" ", strip=True))


def _script_value(html: str, key: str) -> str:
    """Extract simple JavaScript key values from Daum inline config."""
    match = re.search(rf"{re.escape(key)}\s*:\s*'([^']*)'", html)
    return _decode_js_string(match.group(1)) if match else ""


def _comment_number(item: Tag) -> str:
    """Extract a comment number from attributes or child selectors."""
    for attr in ("data-comment-id", "data-id", "id"):
        value = item.get(attr, "")
        if value:
            digits = re.sub(r"[^\d]", "", value)
            if digits:
                return digits
    return _text(item, "comments", "number")


def _js_string(block: str, key: str) -> str:
    """Extract and decode a single-quoted string from an article block."""
    match = re.search(rf"{re.escape(key)}\s*:\s*'((?:\\.|[^'])*)'", block)
    if not match:
        return ""
    return _decode_js_string(match.group(1))


def _js_int(block: str, key: str) -> int:
    """Extract an integer value from an article block."""
    match = re.search(rf"{re.escape(key)}\s*:\s*(\d+)", block)
    return int(match.group(1)) if match else 0


def _js_bool(block: str, key: str) -> bool:
    """Extract Daum Cafe boolean expressions like hasImage: 'Y' == 'Y'."""
    match = re.search(rf"{re.escape(key)}\s*:\s*'([^']*)'\s*==\s*'Y'", block)
    return bool(match and match.group(1) == "Y")


def _decode_js_string(value: str) -> str:
    """Decode escaped JavaScript strings while leaving plain Korean intact."""
    if "\\" not in value:
        return value
    return bytes(value, "utf-8").decode("unicode_escape")
