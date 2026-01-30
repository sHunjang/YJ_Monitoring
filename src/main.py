# ==============================================
# 메인 프로그램 (콘솔 버전)
# ==============================================
"""
여주 센서 모니터링 시스템 - 콘솔 버전

사용법:
    python src/main.py

기능:
1. 데이터베이스 초기화
2. 통합 데이터 수집 시작
3. 프로그램 종료 시 정리
"""

import sys
import signal
import logging
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from core.config import get_config
from core.logging_config import setup_logging
from core.database import initialize_connection_pool, close_connection_pool, test_db_connection
from services.data_collection_service import DataCollectionService

logger = logging.getLogger(__name__)

# 전역 변수
data_service: DataCollectionService = None
shutdown_flag = False


def signal_handler(signum, frame):
    """
    시그널 핸들러 (Ctrl+C)
    
    Args:
        signum: 시그널 번호
        frame: 현재 스택 프레임
    """
    global shutdown_flag
    logger.info("=" * 70)
    logger.info("종료 신호 받음 (Ctrl+C)")
    logger.info("=" * 70)
    shutdown_flag = True


def cleanup():
    """
    프로그램 종료 시 정리 작업
    """
    global data_service
    
    logger.info("=" * 70)
    logger.info("프로그램 종료 작업 시작")
    logger.info("=" * 70)
    
    # 데이터 수집 중지
    if data_service:
        logger.info("데이터 수집 중지 중...")
        data_service.stop()
    
    # 데이터베이스 연결 종료
    logger.info("데이터베이스 연결 종료 중...")
    close_connection_pool()
    
    logger.info("=" * 70)
    logger.info("프로그램 종료 완료")
    logger.info("=" * 70)


def main():
    """메인 함수"""
    global data_service, shutdown_flag
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 초기화
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # 로깅 설정
    setup_logging(log_level="INFO")
    
    # 설정 로드
    config = get_config()
    
    logger.info("=" * 70)
    logger.info(f"{config.app_name} v{config.app_version}")
    logger.info("=" * 70)
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 데이터베이스 연결
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info("데이터베이스 초기화 중...")
    
    try:
        initialize_connection_pool()
        
        if not test_db_connection():
            logger.error("✗ 데이터베이스 연결 실패")
            logger.error("다음을 확인하세요:")
            logger.error("  1. PostgreSQL이 실행 중인지")
            logger.error("  2. .env 파일의 DB 설정이 올바른지")
            logger.error("  3. python src/core/init_db.py를 실행했는지")
            return 1
        
        logger.info("✓ 데이터베이스 연결 성공")
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}", exc_info=True)
        return 1
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 데이터 수집 서비스 시작
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info("데이터 수집 서비스 초기화 중...")
    
    try:
        data_service = DataCollectionService()
        
        # 수집 시작
        data_service.start()
        
        logger.info("✓ 데이터 수집 서비스 시작됨")
        logger.info(f"수집 주기: {config.collection_interval}초")
        
    except Exception as e:
        logger.error(f"데이터 수집 서비스 시작 실패: {e}", exc_info=True)
        cleanup()
        return 1
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 프로그램 실행 중
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info("=" * 70)
    logger.info("프로그램 실행 중...")
    logger.info("종료하려면 Ctrl+C를 누르세요.")
    logger.info("=" * 70)
    
    try:
        # 메인 루프 (Windows 호환)
        while not shutdown_flag:
            time.sleep(1)  # 1초마다 종료 플래그 체크
        
        logger.info("✓ 정상 종료")
        
    except KeyboardInterrupt:
        logger.info("\n프로그램 종료 요청")
    
    except Exception as e:
        logger.error(f"프로그램 오류: {e}", exc_info=True)
    
    finally:
        cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
