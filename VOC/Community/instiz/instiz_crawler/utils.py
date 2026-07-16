"""
유틸리티 함수: 날짜 변환, 로깅, 재시도 로직
"""

import logging
import time
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Any, Optional
from pathlib import Path
import json

import config


def setup_logger(name: str) -> logging.Logger:
    """로거 설정
    
    Args:
        name: 로거 이름
        
    Returns:
        Logger 인스턴스
    """
    # parameters: 로그 디렉토리 생성
    log_dir = Path(config.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # parameters: 로거 생성
    logger = logging.getLogger(name)
    
    # parameters: 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()
    
    # parameters: 로그 레벨 설정
    log_level = getattr(logging, config.LOG_LEVEL)
    logger.setLevel(log_level)
    
    # parameters: 파일 핸들러
    file_handler = logging.FileHandler(
        config.LOG_FILE, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    
    # parameters: 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # parameters: 포매터
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger(__name__)


def convert_date(date_str: str) -> str:
    """날짜 문자열을 YY.MM.DD 형식으로 변환
    
    '오늘', '어제', '1시간 전' 등을 실제 날짜로 변환
    
    Args:
        date_str: 원본 날짜 문자열
        
    Returns:
        YY.MM.DD 형식의 날짜
    """
    # parameters: 현재 시간 기준
    now = datetime.now()
    
    # parameters: '오늘' 처리
    if date_str.strip() == "오늘":
        return now.strftime("%y.%m.%d")
    
    # parameters: '어제' 처리
    if date_str.strip() == "어제":
        yesterday = now - timedelta(days=1)
        return yesterday.strftime("%y.%m.%d")
    
    # parameters: '시간 전' 처리
    if "시간" in date_str:
        try:
            hours = int(date_str.split("시간")[0].strip())
            target_date = now - timedelta(hours=hours)
            return target_date.strftime("%y.%m.%d")
        except (ValueError, IndexError):
            pass
    
    # parameters: '분 전' 처리
    if "분" in date_str:
        try:
            minutes = int(date_str.split("분")[0].strip())
            target_date = now - timedelta(minutes=minutes)
            return target_date.strftime("%y.%m.%d")
        except (ValueError, IndexError):
            pass
    
    # parameters: '일 전' 처리
    if "일" in date_str:
        try:
            days = int(date_str.split("일")[0].strip())
            target_date = now - timedelta(days=days)
            return target_date.strftime("%y.%m.%d")
        except (ValueError, IndexError):
            pass
    
    # parameters: 'YYYY.MM.DD' 또는 'YY.MM.DD' 형식
    if "." in date_str:
        try:
            parts = date_str.split(".")
            if len(parts) == 3:
                year, month, day = parts
                year = int(year)
                
                # parameters: YY 형식 처리 (2자리)
                if year < 100:
                    year += 2000
                
                # parameters: YYYY 형식 처리 (4자리)
                parsed_date = datetime(int(year), int(month), int(day))
                
                # parameters: YY.MM.DD 형식 반환
                year_yy = parsed_date.year % 100
                return f"{year_yy:02d}.{parsed_date.month:02d}.{parsed_date.day:02d}"
        except (ValueError, IndexError):
            pass
    
    # parameters: 파싱 실패 시 현재 날짜 반환
    logger.warning(f"날짜 파싱 실패: {date_str} → 현재 날짜로 대체")
    return now.strftime("%y.%m.%d")


def retry(
    max_attempts: int = config.MAX_RETRY,
    delay: float = 1.0,
    backoff: float = 1.5
) -> Callable:
    """재시도 데코레이터
    
    지정된 횟수만큼 자동으로 재시도하며, 각 시도 사이에 지연을 추가
    
    Args:
        max_attempts: 최대 시도 횟수
        delay: 초기 지연 시간 (초)
        backoff: 지수 백오프 배수
        
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} 최대 재시도 {max_attempts}회 실패: {str(e)}"
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} 재시도 {attempt}/{max_attempts} "
                        f"({current_delay:.1f}초 후)"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_delay(include_random: bool = True) -> float:
    """요청 지연 시간 반환
    
    Args:
        include_random: 랜덤 지연 포함 여부
        
    Returns:
        지연 시간 (초)
    """
    delay = config.REQUEST_DELAY
    
    if include_random and config.REQUEST_DELAY_RANDOM:
        import random
        # parameters: ±20% 랜덤 지연
        random_factor = random.uniform(0.8, 1.2)
        delay *= random_factor
    
    return delay


def save_json(data: dict, filepath: str) -> None:
    """JSON 파일 저장
    
    Args:
        data: 저장할 데이터
        filepath: 저장 경로
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(filepath: str) -> Optional[dict]:
    """JSON 파일 로드
    
    Args:
        filepath: 로드할 파일 경로
        
    Returns:
        로드된 데이터 또는 None
    """
    path = Path(filepath)
    if not path.exists():
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON 로드 실패: {filepath} - {str(e)}")
        return None


def format_runtime(seconds: float) -> str:
    """실행 시간을 읽기 쉬운 형식으로 변환
    
    Args:
        seconds: 초 단위 시간
        
    Returns:
        포매팅된 시간 문자열
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}시간 {minutes}분 {secs}초"
    elif minutes > 0:
        return f"{minutes}분 {secs}초"
    else:
        return f"{secs}초"


def safe_filename(value: str) -> str:
    """파일명에 안전한 문자열로 변환."""
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", str(value)).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "keyword"
