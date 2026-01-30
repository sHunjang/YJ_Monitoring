# ==============================================
# 로깅 설정 모듈
# ==============================================
"""
애플리케이션 전체의 로깅 설정

주요 기능:
1. 콘솔 출력 (색상 포함)
2. 파일 출력 (로테이션)
3. 로그 레벨 설정
4. 포맷 설정

사용 예:
    from core.logging_config import setup_logging
    
    setup_logging()
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info("애플리케이션 시작")
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

try:
    # 색상 로그 (선택사항)
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
):
    """
    로깅 설정 초기화
    
    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (None이면 파일 출력 안 함)
        max_bytes: 로그 파일 최대 크기 (바이트)
        backup_count: 로그 파일 백업 개수
        console_output: 콘솔 출력 여부
        
    Example:
        >>> setup_logging(log_level="DEBUG", log_file="logs/app.log")
    """
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 로그 레벨 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 문자열을 logging 상수로 변환
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    level = level_map.get(log_level.upper(), logging.INFO)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 루트 로거 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 콘솔 핸들러 (색상 지원)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # 색상 포맷 (colorlog 사용 가능 시)
        if HAS_COLORLOG:
            # 색상이 있는 포맷
            console_format = (
                '%(log_color)s%(asctime)s | '
                '%(levelname)-8s | '
                '%(name)s | '
                '%(message)s%(reset)s'
            )
            console_formatter = colorlog.ColoredFormatter(
                console_format,
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            # 색상 없는 기본 포맷
            console_format = (
                '%(asctime)s | '
                '%(levelname)-8s | '
                '%(name)s | '
                '%(message)s'
            )
            console_formatter = logging.Formatter(
                console_format,
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. 파일 핸들러 (로테이션)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if log_file:
        # 로그 파일 디렉토리 생성
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 로테이팅 파일 핸들러
        # 파일 크기가 max_bytes를 초과하면 자동으로 백업 생성
        # 예: app.log → app.log.1 → app.log.2 → ...
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # 파일 포맷 (색상 없음)
        file_format = (
            '%(asctime)s | '
            '%(levelname)-8s | '
            '%(name)s | '
            '%(funcName)s:%(lineno)d | '
            '%(message)s'
        )
        file_formatter = logging.Formatter(
            file_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. 외부 라이브러리 로그 레벨 조정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # pymodbus 로그는 WARNING 이상만 출력
    logging.getLogger('pymodbus').setLevel(logging.WARNING)
    
    # matplotlib 로그는 WARNING 이상만 출력
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    # PIL 로그는 WARNING 이상만 출력
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. 로깅 시작 메시지
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("로깅 시스템 초기화 완료")
    logger.info("=" * 70)
    logger.info(f"로그 레벨: {log_level}")
    if log_file:
        logger.info(f"로그 파일: {log_file}")
        logger.info(f"파일 최대 크기: {max_bytes / 1024 / 1024:.1f} MB")
        logger.info(f"백업 개수: {backup_count}")
    logger.info("=" * 70)


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 생성
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
        
    Returns:
        logging.Logger: 로거 객체
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("메시지")
    """
    return logging.getLogger(name)


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """
    이 파일을 직접 실행하면 로깅 테스트
    
    실행 방법:
        python src/core/logging_config.py
    """
    # 로깅 설정
    setup_logging(
        log_level="DEBUG",
        log_file="logs/test.log",
        console_output=True
    )
    
    # 테스트 로거
    logger = get_logger(__name__)
    
    print("\n로그 레벨 테스트:\n")
    logger.debug("🔍 DEBUG 메시지 - 디버깅 정보")
    logger.info("ℹ️  INFO 메시지 - 일반 정보")
    logger.warning("⚠️  WARNING 메시지 - 경고")
    logger.error("❌ ERROR 메시지 - 오류")
    logger.critical("🚨 CRITICAL 메시지 - 심각한 오류")
    
    print("\n✓ 로그가 콘솔과 logs/test.log 파일에 저장되었습니다.")
