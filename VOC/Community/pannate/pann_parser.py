"""
Nate Pann HTML 파싱 전담
"""
import re
from typing import Optional, List, Tuple, Dict, Any
from bs4 import BeautifulSoup, Tag
import logging

import utils

logger = utils.setup_logger(__name__)


class PannParser:
    """네이트 판 HTML 파서"""

    # 게시판 목록 페이지 Selectors
    POST_ITEM_SELECTOR = "tr.list-item"
    POST_CATEGORY_SELECTOR = "td.subject a.cate"
    POST_TITLE_SELECTOR = "td.subject a.tit"
    POST_AUTHOR_SELECTOR = "td.writer"
    POST_DATE_SELECTOR = "td.date"
    POST_VIEW_COUNT_SELECTOR = "td.view"
    POST_RECOMMEND_COUNT_SELECTOR = "td.recom"
    POST_COMMENT_COUNT_SELECTOR = "td.subject .cmt"

    # 게시글 상세 페이지 Selectors
    POST_DETAIL_TITLE_SELECTOR = "div.post-tit-info h1"
    POST_DETAIL_AUTHOR_SELECTOR = "div.user-info a.nick"
    POST_DETAIL_DATE_SELECTOR = "div.user-info .date"
    POST_DETAIL_VIEW_COUNT_SELECTOR = "div.user-info .view"
    POST_DETAIL_RECOMMEND_COUNT_SELECTOR = "div.info-recom span.count"
    POST_DETAIL_OPPOSE_COUNT_SELECTOR = "div.info-oppose span.count"
    POST_DETAIL_CONTENT_SELECTOR = "div#contentArea"

    # 댓글 Selectors
    COMMENT_ITEM_SELECTOR = "div#commentDiv > dl"
    COMMENT_AUTHOR_SELECTOR = "dt a.name"
    COMMENT_CONTENT_SELECTOR = "dd.usertxt"
    COMMENT_DATE_SELECTOR = "dt span.date"
    COMMENT_RECOMMEND_SELECTOR = "button.btn_recom span.num"

    @staticmethod
    def parse_board_list(html: str, board_name: str) -> List[Dict[str, Any]]:
        """
        게시판 목록 페이지를 파싱하여 게시글 정보 리스트를 반환합니다.

        Args:
            html: 게시판 목록 HTML 문자열
            board_name: 게시판 이름

        Returns:
            게시글 정보 딕셔너리의 리스트
        """
        posts = []
        seen_urls = set()
        soup = BeautifulSoup(html, "html.parser")
        post_items = soup.select(PannParser.POST_ITEM_SELECTOR)

        if not post_items:
            logger.warning("게시물 목록을 찾을 수 없습니다. Selector를 확인하세요.")
            return []

        for item in post_items:
            try:
                title_elem = item.select_one(PannParser.POST_TITLE_SELECTOR)
                if not title_elem:
                    continue

                url = title_elem.get("href")
                if url and not url.startswith("http"):
                    url = f"https://pann.nate.com{url}"

                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                article_id_match = re.search(r'/talk/(\d+)', url)
                article_id = int(article_id_match.group(1)) if article_id_match else 0

                category_elem = item.select_one(PannParser.POST_CATEGORY_SELECTOR)

                post = {
                    "title": title_elem.get_text(strip=True),
                    "url": url,
                    "article_id": article_id,
                    "author": item.select_one(PannParser.POST_AUTHOR_SELECTOR).get_text(strip=True),
                    "created_at": item.select_one(PannParser.POST_DATE_SELECTOR).get_text(strip=True),
                    "view_count": int(item.select_one(PannParser.POST_VIEW_COUNT_SELECTOR).get_text(strip=True).replace(',', '')),
                    "recommend_count": int(item.select_one(PannParser.POST_RECOMMEND_COUNT_SELECTOR).get_text(strip=True).replace(',', '')),
                    "comment_count": int(item.select_one(PannParser.POST_COMMENT_COUNT_SELECTOR).get_text(strip=True) or 0),
                    "category": category_elem.get_text(strip=True) if category_elem else None,
                    "board_name": board_name,
                }
                posts.append(post)
            except (AttributeError, ValueError, TypeError) as e:
                logger.warning(f"게시판 목록의 일부 항목 파싱 실패: {e}")
                continue
        return posts

    @staticmethod
    def parse_post_detail(html: str) -> Dict[str, Any]:
        """
        게시글 상세 페이지를 파싱하여 상세 정보를 반환합니다.

        Args:
            html: 게시글 상세 HTML 문자열

        Returns:
            게시글 상세 정보 딕셔너리
        """
        soup = BeautifulSoup(html, "html.parser")
        details = {}

        try:
            # 필수 정보 추출
            details["title"] = soup.select_one(PannParser.POST_DETAIL_TITLE_SELECTOR).get_text(strip=True)
            details["author"] = soup.select_one(PannParser.POST_DETAIL_AUTHOR_SELECTOR).get_text(strip=True)
            details["created_at"] = soup.select_one(PannParser.POST_DETAIL_DATE_SELECTOR).get_text(strip=True)

            # 본문 추출 및 정제
            content_elem = soup.select_one(PannParser.POST_DETAIL_CONTENT_SELECTOR)
            if content_elem:
                # 광고, 관련 글 등 불필요한 요소 제거
                for ad_elem in content_elem.select('.pann-ad, .another-pann, script'):
                    ad_elem.decompose()
                details["content"] = content_elem.get_text(separator="\n", strip=True)
                details["images"] = [img['src'] for img in content_elem.find_all('img') if 'src' in img.attrs]
            else:
                details["content"] = ""
                details["images"] = []

            # 숫자 정보 추출
            view_text = soup.select_one(PannParser.POST_DETAIL_VIEW_COUNT_SELECTOR).get_text(strip=True)
            details["view_count"] = int(re.search(r'[\d,]+', view_text).group(0).replace(',', ''))

            recommend_elem = soup.select_one(PannParser.POST_DETAIL_RECOMMEND_COUNT_SELECTOR)
            details["recommend_count"] = int(recommend_elem.get_text(strip=True)) if recommend_elem else 0

            oppose_elem = soup.select_one(PannParser.POST_DETAIL_OPPOSE_COUNT_SELECTOR)
            details["oppose_count"] = int(oppose_elem.get_text(strip=True)) if oppose_elem else 0

        except (AttributeError, ValueError, TypeError) as e:
            logger.error(f"게시글 상세 정보 파싱 중 오류 발생: {e}")
            # 필수 값이 없으면 빈 딕셔너리 반환
            return {}

        return details

    @staticmethod
    def parse_comments(html: str) -> List[Dict[str, Any]]:
        """
        댓글 정보를 파싱합니다.

        Args:
            html: 댓글이 포함된 HTML 문자열

        Returns:
            댓글 정보 딕셔너리의 리스트
        """
        comments = []
        soup = BeautifulSoup(html, "html.parser")
        comment_items = soup.select(PannParser.COMMENT_ITEM_SELECTOR)

        if not comment_items:
            logger.info("댓글이 없습니다.")
            return []

        for item in comment_items:
            try:
                # 대댓글(dd.reply-box)은 구조가 다르므로 건너뜁니다.
                if item.find_parent("dd", class_="reply-box"):
                    continue

                author_elem = item.select_one(PannParser.COMMENT_AUTHOR_SELECTOR)
                content_elem = item.select_one(PannParser.COMMENT_CONTENT_SELECTOR)
                date_elem = item.select_one(PannParser.COMMENT_DATE_SELECTOR)
                recom_elem = item.select_one(PannParser.COMMENT_RECOMMEND_SELECTOR)

                if not all([author_elem, content_elem, date_elem]):
                    continue

                # 댓글 내용에서 답글쓰기, 신고 등 버튼 텍스트 제거
                for btn_elem in content_elem.select('.btn_reply, .btn_report'):
                    btn_elem.decompose()

                comment = {
                    "author": author_elem.get_text(strip=True),
                    "content": content_elem.get_text(strip=True),
                    "created_at": date_elem.get_text(strip=True),
                    "recommend_count": int(recom_elem.get_text(strip=True)) if recom_elem else 0,
                }
                comments.append(comment)
            except (AttributeError, ValueError, TypeError) as e:
                logger.warning(f"댓글 파싱 중 오류 발생: {e}")
                continue

        return comments

    @staticmethod
    def needs_playwright_for_comments() -> bool:
        """
        네이트 판은 댓글이 HTML에 정적으로 포함되어 있으므로 Playwright가 필요하지 않습니다.
        """
        return False