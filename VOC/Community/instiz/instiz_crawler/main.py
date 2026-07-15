"""
메인 실행 파일
"""

import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

import config
import utils
from crawler import InstizCrawler
from models import Post, Comment

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


def save_to_csv(posts: list, comments_dict: dict = None, board: str = "", start: int = 1, end: int = 1) -> None:
    """CSV 파일로 저장
    
    Args:
        posts: Post 객체 리스트
        comments_dict: 댓글 정보 딕셔너리
        board: 게시판 이름
        start: 시작 페이지
        end: 종료 페이지
    """
    import csv
    
    if not posts:
        logger.warning("저장할 게시글이 없습니다")
        return
    
    # parameters: 출력 디렉토리 생성
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # parameters: 게시글 CSV 파일명
    post_csv = output_dir / f"instiz_{board}_{start}_{end}.csv"
    
    try:
        # parameters: 게시글 CSV 저장
        with open(post_csv, "w", newline="", encoding=config.CSV_ENCODING) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=config.REQUIRED_POST_COLUMNS + (["content"] if config.CRAWL_CONTENT else []),
                restval=""
            )
            writer.writeheader()
            
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
                
                if config.CRAWL_CONTENT:
                    row["content"] = post.content or ""
                
                writer.writerow(row)
        
        logger.info(f"게시글 CSV 저장 완료: {post_csv} ({len(posts)}개)")
        
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
                comment_csv = output_dir / f"instiz_{board}_{start}_{end}_comments.csv"
                
                with open(comment_csv, "w", newline="", encoding=config.CSV_ENCODING) as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=config.REQUIRED_COMMENT_COLUMNS,
                        restval=""
                    )
                    writer.writeheader()
                    
                    for comment in all_comments:
                        writer.writerow(comment.to_dict())
                
                logger.info(f"댓글 CSV 저장 완료: {comment_csv} ({len(all_comments)}개)")
    
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
        
        if not targets:
            logger.error("크롤링할 게시판이 설정되지 않았습니다")
            sys.exit(1)
        
        # parameters: 크롤러 생성 및 브라우저 초기화
        crawler = InstizCrawler()
        crawler.start_browser()
        
        # parameters: 각 게시판 크롤링
        all_posts = []
        all_comments = {}
        
        for target in targets:
            board = target["board"]
            category = target["category"]
            start = target["start"]
            end = target["end"]
            
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
