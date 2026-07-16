"""
메인 실행 파일
"""

import sys
import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
import csv

import config
import utils
from crawler import InstizCrawler
from models import Post, Comment

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = utils.setup_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """CLI 인자 파싱
    
    Returns:
        파싱된 인자
    """
    parser = argparse.ArgumentParser(
        description="인스티즈(instiz) 게시판 크롤러",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py --board name_beauty --category 12 --start 1 --end 10
  python main.py --board name_fashion --start 1 --end 30 --no-content
  $env:INSTIZ_ID="your_id"; $env:INSTIZ_PASSWORD="your_password"
  python main.py --login --keyword "키워드" --board name_beauty --category 12
        """
    )
    
    # parameters: 게시판 옵션
    parser.add_argument(
        "--board",
        type=str,
        default=None,
        help="크롤링할 게시판 (기본값: config.py의 BOARDS)"
    )
    
    # parameters: 카테고리 옵션
    parser.add_argument(
        "--category",
        type=int,
        default=None,
        help="카테고리 번호 (기본값: config.py의 카테고리)"
    )
    
    # parameters: 페이지 범위
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="시작 페이지 (기본값: config.py의 START_PAGE)"
    )
    
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="종료 페이지 (기본값: config.py의 END_PAGE)"
    )

    # parameters: 검색 옵션
    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="검색 키워드 1개. 지정하면 게시판 페이지 순회 대신 검색 결과를 수집"
    )

    parser.add_argument(
        "--keywords",
        nargs="+",
        default=None,
        help="검색 키워드 여러 개"
    )

    parser.add_argument(
        "--max-more-clicks",
        type=int,
        default=None,
        help="검색 결과 더보기 최대 클릭 횟수"
    )

    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="검색 키워드당 최대 게시글 수 (0이면 제한 없음)"
    )

    parser.add_argument(
        "--search-type",
        type=int,
        choices=[1, 5, 9],
        default=None,
        help="검색 범위: 1=제목, 5=내용, 9=제목+내용"
    )

    parser.add_argument(
        "--search-endpoint",
        choices=["popup", "board"],
        default=None,
        help="검색 엔드포인트: popup=더보기형 통합검색, board=게시판 list.php 검색"
    )

    parser.add_argument(
        "--search-all-boards",
        action="store_true",
        help="board/category를 무시하고 전체 검색 결과만 수집"
    )

    # parameters: 로그인 옵션
    parser.add_argument(
        "--login",
        action="store_true",
        help="크롤링 전 로그인 수행 (INSTIZ_ID / INSTIZ_PASSWORD 환경변수 권장)"
    )

    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="인스티즈 아이디. 보안상 INSTIZ_ID 환경변수 사용 권장"
    )

    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="인스티즈 비밀번호. 보안상 INSTIZ_PASSWORD 환경변수 사용 권장"
    )

    parser.add_argument(
        "--storage-state",
        type=str,
        default=None,
        help="로그인 세션 저장/로드 파일 경로"
    )

    parser.add_argument(
        "--no-save-login-state",
        action="store_true",
        help="로그인 성공 후 세션 파일을 저장하지 않음"
    )

    parser.add_argument(
        "--manual-login-wait",
        type=int,
        default=None,
        help="브라우저에서 직접 로그인할 시간을 초 단위로 대기"
    )

    parser.add_argument(
        "--headed",
        action="store_true",
        help="브라우저 창을 표시"
    )
    
    # parameters: 크롤링 옵션
    parser.add_argument(
        "--no-content",
        action="store_true",
        help="본문 및 댓글 수집 안 함"
    )
    
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="댓글만 수집 안 함 (본문은 수집)"
    )
    
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="HTML 파일 저장"
    )
    
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="캐시 사용"
    )
    
    # parameters: 출력 옵션
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 로그 출력"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="로그 레벨 (기본값: config.py의 LOG_LEVEL)"
    )
    
    return parser.parse_args()


def apply_cli_arguments(args: argparse.Namespace) -> None:
    """CLI 인자를 config에 적용 (CLI 옵션이 config.py보다 우선)
    
    Args:
        args: 파싱된 CLI 인자
    """
    # parameters: 본문 수집 옵션
    if args.no_content:
        config.CRAWL_CONTENT = False
    
    # parameters: 댓글 수집 옵션
    if args.no_comments:
        config.CRAWL_COMMENT = False
    
    # parameters: HTML 저장 옵션
    if args.save_html:
        config.SAVE_HTML = True
    
    # parameters: 캐시 옵션
    if args.use_cache:
        config.USE_CACHE = True

    if args.search_type is not None:
        config.SEARCH_TYPE = args.search_type

    if args.search_endpoint is not None:
        config.SEARCH_ENDPOINT = args.search_endpoint

    if args.search_all_boards:
        config.SEARCH_ALL_BOARDS = True

    if args.max_more_clicks is not None:
        config.MAX_MORE_CLICKS = args.max_more_clicks

    if args.max_posts is not None:
        config.MAX_SEARCH_POSTS = args.max_posts

    if args.login:
        config.LOGIN_ENABLED = True

    if args.username:
        config.LOGIN_USERNAME = args.username

    if args.password:
        config.LOGIN_PASSWORD = args.password

    if args.storage_state:
        config.LOGIN_STORAGE_STATE = args.storage_state

    if args.no_save_login_state:
        config.SAVE_LOGIN_STATE = False

    if args.manual_login_wait is not None:
        config.MANUAL_LOGIN_WAIT_SECONDS = args.manual_login_wait
        if args.manual_login_wait > 0:
            config.LOGIN_ENABLED = True

    if args.headed:
        config.HEADLESS = False
    
    # parameters: 로그 레벨
    if args.log_level:
        config.LOG_LEVEL = args.log_level
    
    # parameters: 상세 로그
    if args.verbose:
        config.LOG_LEVEL = "DEBUG"


def get_crawl_targets(args: argparse.Namespace) -> list:
    """크롤링 대상 게시판 결정
    
    Args:
        args: 파싱된 CLI 인자
        
    Returns:
        크롤링 대상 리스트: [{"board": "...", "category": ..., "start": ..., "end": ...}]
    """
    targets = []
    
    # parameters: CLI 옵션으로 보드가 지정된 경우
    if args.board:
        target = {
            "board": args.board,
            "category": args.category or 12,
            "start": args.start or config.START_PAGE,
            "end": args.end or config.END_PAGE
        }
        targets.append(target)
    else:
        # parameters: config.py의 BOARDS 사용
        for board_config in config.BOARDS:
            target = {
                "board": board_config["board"],
                "category": board_config.get("category", 12),
                "start": args.start or config.START_PAGE,
                "end": args.end or config.END_PAGE
            }
            targets.append(target)
    
    return targets


def get_search_keywords(args: argparse.Namespace) -> list:
    """CLI/config에서 검색 키워드 목록 결정."""
    keywords = []
    if args.keyword:
        keywords.append(args.keyword)
    if args.keywords:
        keywords.extend(args.keywords)
    if not keywords:
        keywords.extend(getattr(config, "SEARCH_KEYWORDS", []))
    return [str(keyword).strip() for keyword in keywords if str(keyword).strip()]


def get_login_credentials() -> tuple:
    """환경변수/config에서 로그인 계정 정보를 가져옵니다."""
    username = os.getenv("INSTIZ_ID") or getattr(config, "LOGIN_USERNAME", "")
    password = os.getenv("INSTIZ_PASSWORD") or getattr(config, "LOGIN_PASSWORD", "")
    return username.strip(), password


def save_to_csv(
    posts: list,
    comments_dict: dict = None,
    board: str = "",
    start: int = 1,
    end: int = 1,
    output_name: str = None
) -> None:
    """CSV 파일로 저장
    
    Args:
        posts: Post 객체 리스트
        comments_dict: 댓글 정보 딕셔너리
        board: 게시판 이름
        start: 시작 페이지
        end: 종료 페이지
    """
    if not posts:
        logger.warning("저장할 게시글이 없습니다")
        return
    
    # parameters: 출력 디렉토리 생성
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # parameters: 게시글 CSV 파일명
    file_stem = output_name or f"instiz_{board}_{start}_{end}"
    post_csv = output_dir / f"{file_stem}.csv"
    
    try:
        fieldnames = config.REQUIRED_POST_COLUMNS + ["content"]
        existing_rows = {}
        if post_csv.exists():
            with open(post_csv, "r", newline="", encoding=config.CSV_ENCODING) as f:
                for row in csv.DictReader(f):
                    post_id = str(row.get("post_id", "")).strip()
                    row_board = str(row.get("board", "")).strip()
                    if post_id:
                        existing_rows[f"{row_board}:{post_id}"] = row

        incoming_rows = {}
        for post in posts:
            row = {
                "post_id": post.post_id,
                "board": post.board,
                "category": post.category,
                "title": post.title,
                "author": post.author,
                "comment_count": post.comment_count,
                "view_count": post.view_count,
                "like_count": post.like_count,
                "created_date": post.created_date,
                "has_image": post.has_image,
                "image_count": post.image_count,
                "post_url": post.post_url
            }

            row["content"] = post.content or ""

            incoming_rows[f"{post.board}:{post.post_id}"] = row

        merged_rows = {**existing_rows, **incoming_rows}

        # parameters: 게시글 CSV 저장
        with open(post_csv, "w", newline="", encoding=config.CSV_ENCODING) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                restval=""
            )
            writer.writeheader()
            
            for row in sorted(merged_rows.values(), key=lambda item: int(item.get("post_id") or 0), reverse=True):
                writer.writerow(row)
        
        logger.info(f"게시글 CSV 저장 완료: {post_csv} (new={len(posts)}, total={len(merged_rows)})")
        
        # parameters: 댓글 CSV 저장
        if config.CRAWL_COMMENT and comments_dict:
            all_comments = []
            for post_id, details in comments_dict.items():
                comments = details.get("comments", [])
                for comment_number, author, created_time, is_reply, content in comments:
                    all_comments.append(Comment(
                        post_id=post_id,
                        post_url=details["post"].post_url,
                        comment_number=comment_number,
                        author=author,
                        created_time=created_time,
                        is_reply=is_reply,
                        content=content
                    ))
            
            if all_comments:
                comment_csv = output_dir / f"{file_stem}_comments.csv"
                existing_comments = {}
                if comment_csv.exists():
                    with open(comment_csv, "r", newline="", encoding=config.CSV_ENCODING) as f:
                        for row in csv.DictReader(f):
                            key = (
                                str(row.get("post_url", "")),
                                str(row.get("post_id", "")),
                                str(row.get("comment_number", "")),
                                str(row.get("created_time", "")),
                                str(row.get("content", "")),
                            )
                            existing_comments[key] = row

                incoming_comments = {}
                for comment in all_comments:
                    row = comment.to_dict()
                    key = (
                        str(row.get("post_url", "")),
                        str(row.get("post_id", "")),
                        str(row.get("comment_number", "")),
                        str(row.get("created_time", "")),
                        str(row.get("content", "")),
                    )
                    incoming_comments[key] = row

                merged_comments = {**existing_comments, **incoming_comments}
                
                with open(comment_csv, "w", newline="", encoding=config.CSV_ENCODING) as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=config.REQUIRED_COMMENT_COLUMNS,
                        restval=""
                    )
                    writer.writeheader()
                    
                    for row in merged_comments.values():
                        writer.writerow(row)
                
                logger.info(f"댓글 CSV 저장 완료: {comment_csv} (new={len(all_comments)}, total={len(merged_comments)})")
    
    except Exception as e:
        logger.error(f"CSV 저장 실패: {str(e)}")


def print_statistics(stats: dict) -> None:
    """통계 출력
    
    Args:
        stats: 통계 딕셔너리
    """
    logger.info("=" * 50)
    logger.info("크롤링 완료")
    logger.info("=" * 50)
    logger.info(f"시작 시간: {stats['start_time']}")
    logger.info(f"종료 시간: {stats['end_time']}")
    logger.info(f"실행 시간: {stats['runtime']}")
    logger.info("-" * 50)
    logger.info(f"게시판 수: {stats['boards']}")
    logger.info(f"페이지 수: {stats['pages']}")
    logger.info(f"게시글 수: {stats['posts']}")
    logger.info(f"댓글 수: {stats['comments']}")
    logger.info("-" * 50)
    logger.info(f"오류 수: {stats['errors']}")
    logger.info(f"재시도 횟수: {stats['retries']}")
    logger.info(f"평균 처리 속도: {stats['average_speed']}")
    logger.info("=" * 50)


def main():
    """메인 실행 함수"""
    crawler = None
    try:
        logger.info("인스티즈 크롤러 시작")
        
        # parameters: CLI 인자 파싱
        args = parse_arguments()
        
        # parameters: CLI 인자를 config에 적용
        apply_cli_arguments(args)
        
        # parameters: 크롤링 대상 결정
        targets = get_crawl_targets(args)
        search_keywords = get_search_keywords(args)
        
        if not targets and not (search_keywords and getattr(config, "SEARCH_ALL_BOARDS", False)):
            logger.error("크롤링할 게시판이 설정되지 않았습니다")
            sys.exit(1)
        
        # parameters: 크롤러 생성 및 브라우저 초기화
        crawler = InstizCrawler()
        crawler.start_browser()

        username, password = get_login_credentials()
        if config.LOGIN_ENABLED or username or password:
            if not crawler.login(username=username, password=password):
                logger.error("로그인이 필요한 작업을 계속할 수 없어 종료합니다")
                sys.exit(1)
        
        # parameters: 각 게시판 크롤링
        all_posts = []
        all_comments = {}

        if search_keywords and getattr(config, "SEARCH_ALL_BOARDS", False):
            logger.info(f"\n전체 검색 크롤링: 키워드: {', '.join(search_keywords)}")

            for keyword in search_keywords:
                posts, post_details = crawler.crawl_search(
                    board="",
                    category=0,
                    keyword=keyword,
                    max_more_clicks=config.MAX_MORE_CLICKS,
                    max_posts=config.MAX_SEARCH_POSTS,
                )

                if config.CRAWL_CONTENT and posts:
                    post_details = crawler.crawl_post_contents(posts)
                    posts = [pd["post"] for pd in post_details.values()]

                output_name = f"instiz_search_{utils.safe_filename(keyword)}"
                save_to_csv(posts, post_details, "search", 0, 0, output_name=output_name)

                all_posts.extend(posts)
                all_comments.update(post_details)

            stats = crawler.get_statistics()
            print_statistics(stats)
            logger.info("인스티즈 크롤러 종료")
            return
        
        for target in targets:
            board = target["board"]
            category = target["category"]
            start = target["start"]
            end = target["end"]
            
            if search_keywords:
                logger.info(
                    f"\n검색 크롤링: {board} "
                    f"(카테고리: {category}, 키워드: {', '.join(search_keywords)})"
                )

                for keyword in search_keywords:
                    posts, post_details = crawler.crawl_search(
                        board=board,
                        category=category,
                        keyword=keyword,
                        max_more_clicks=config.MAX_MORE_CLICKS,
                        max_posts=config.MAX_SEARCH_POSTS,
                    )

                    if config.CRAWL_CONTENT and posts:
                        post_details = crawler.crawl_post_contents(posts)
                        posts = [pd["post"] for pd in post_details.values()]

                    output_name = f"instiz_{board}_search_{utils.safe_filename(keyword)}"
                    save_to_csv(posts, post_details, board, start, end, output_name=output_name)

                    all_posts.extend(posts)
                    all_comments.update(post_details)
            else:
                logger.info(f"\n게시판 크롤링: {board} (카테고리: {category}, 페이지: {start}~{end})")
                
                # parameters: 1단계: 게시글 목록 수집
                posts, post_details = crawler.crawl_board(board, category, start, end)
                
                # parameters: 2단계: 게시글 본문 및 댓글 수집
                if config.CRAWL_CONTENT and posts:
                    post_details = crawler.crawl_post_contents(posts)
                    posts = [pd["post"] for pd in post_details.values()]
                
                # parameters: CSV 저장
                save_to_csv(posts, post_details, board, start, end)
                
                all_posts.extend(posts)
                all_comments.update(post_details)
        
        # parameters: 통계 출력
        stats = crawler.get_statistics()
        print_statistics(stats)
        
        logger.info("인스티즈 크롤러 종료")
    
    except KeyboardInterrupt:
        logger.warning("\n사용자에 의해 크롤링 중단됨")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {str(e)}", exc_info=True)
        sys.exit(1)
    
    finally:
        # parameters: 브라우저 정리
        if crawler:
            try:
                crawler.close_browser()
            except Exception as e:
                logger.error(f"브라우저 종료 실패: {str(e)}")


if __name__ == "__main__":
    main()
