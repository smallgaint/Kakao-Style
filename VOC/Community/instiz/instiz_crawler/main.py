"""
메인 실행 파일
"""

import sys
import argparse
import logging
import os
from datetime import datetime, date
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
  python main.py --target name:1 name_beauty --keywords 지그재그 29cm --start-date 2026-01-01 --end-date 2026-06-30
  $env:INSTIZ_ID="your_id"; $env:INSTIZ_PASSWORD="your_password"
  python main.py --login --target name:1 --keyword "키워드" --start-date 2026-01-01 --end-date 2026-06-30
        """
    )
    
    # parameters: 게시판 옵션
    parser.add_argument(
        "--target",
        nargs="+",
        default=None,
        metavar="BOARD[:CATEGORY]",
        help="검색 게시판들. 예: --target name:1 name_beauty (기본값: config.py의 BOARDS)"
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

    parser.add_argument("--start-date", type=str, default=None, help="검색 시작일 (YYYY-MM-DD, 포함)")
    parser.add_argument("--end-date", type=str, default=None, help="검색 종료일 (YYYY-MM-DD, 포함)")

    parser.add_argument(
        "--search-type",
        type=int,
        choices=[1, 5, 9],
        default=None,
        help="검색 범위: 1=제목, 5=내용, 9=제목+내용"
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
    
    if args.target:
        for raw_target in args.target:
            board, separator, raw_category = raw_target.partition(":")
            if not board or (separator and (not raw_category or not raw_category.isdigit())):
                raise ValueError(f"잘못된 --target 값: {raw_target}. BOARD 또는 BOARD:CATEGORY 형식을 사용하세요.")
            targets.append({
                "board": board,
                "category": int(raw_category) if separator else None,
                "start": args.start or config.START_PAGE,
                "end": args.end or config.END_PAGE,
            })
    else:
        # parameters: config.py의 BOARDS 사용
        for board_config in config.BOARDS:
            target = {
                "board": board_config["board"],
                "category": board_config.get("category"),
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


def get_search_date_range(args: argparse.Namespace) -> tuple[date, date]:
    """CLI 또는 설정의 검색 기간을 검증해 반환합니다."""
    start_value = args.start_date or config.SEARCH_START_DATE
    end_value = args.end_date or config.SEARCH_END_DATE
    try:
        start_date = datetime.strptime(start_value, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError("--start-date와 --end-date는 YYYY-MM-DD 형식이어야 합니다.") from exc
    if start_date > end_date:
        raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")
    return start_date, end_date


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
                "post_url": post.post_url,
                "search_keywords": post.search_keywords,
                "search_boards": post.search_boards,
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
        
        if not targets:
            logger.error("크롤링할 게시판이 설정되지 않았습니다")
            sys.exit(1)

        if not search_keywords:
            logger.error("검색 키워드가 설정되지 않았습니다. --keyword, --keywords 또는 SEARCH_KEYWORDS를 확인하세요")
            sys.exit(1)
        start_date, end_date = get_search_date_range(args)
        
        # parameters: 크롤러 생성 및 브라우저 초기화
        crawler = InstizCrawler()
        crawler.start_browser()

        username, password = get_login_credentials()
        if config.LOGIN_ENABLED or username or password:
            if not crawler.login(username=username, password=password):
                logger.error("로그인이 필요한 작업을 계속할 수 없어 종료합니다")
                sys.exit(1)
        
        # parameters: 게시판별 검색 목록 수집
        all_posts = []
        logger.info("게시판 검색 크롤링: 기간=%s~%s, 키워드=%s", start_date, end_date, ", ".join(search_keywords))

        for target in targets:
            board = target["board"]
            category = target["category"]
            for keyword in search_keywords:
                all_posts.extend(crawler.crawl_board_search(board, category, keyword, start_date, end_date))

        # parameters: 중복 제거 후 한 번만 상세 수집
        post_details = crawler.crawl_post_contents(all_posts) if config.CRAWL_CONTENT and all_posts else {
            post.post_id: {"post": post, "comments": []} for post in all_posts
        }
        if config.CRAWL_CONTENT:
            all_posts = [details["post"] for details in post_details.values()]
        output_name = f"instiz_board_search_{start_date:%Y%m%d}_{end_date:%Y%m%d}"
        save_to_csv(all_posts, post_details, output_name=output_name)
        
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
