# ==============================================
# 데이터베이스 초기화 스크립트
# ==============================================
"""
PostgreSQL 데이터베이스 테이블 초기화

실행:
    python src/core/init_db.py

기능:
- 기존 테이블 삭제
- 새 테이블 생성
- 인덱스 생성
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from core.logging_config import setup_logging
from core.database import get_db_connection

logger = logging.getLogger(__name__)


def init_database():
    """데이터베이스 초기화"""
    
    logger.info("=" * 70)
    logger.info("데이터베이스 초기화 시작")
    logger.info("=" * 70)
    
    # SQL 파일 경로
    sql_file = project_root / 'sql' / 'init.sql'
    
    if not sql_file.exists():
        logger.error(f"SQL 파일을 찾을 수 없습니다: {sql_file}")
        return False
    
    try:
        # SQL 파일 읽기 (UTF-8)
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        logger.info(f"SQL 파일 읽기 완료: {sql_file}")
        
        # psql 전용 명령어 제거 (\dt, \d 등)
        sql_lines = []
        for line in sql_script.split('\n'):
            # \로 시작하는 줄 제거 (psql 메타 명령어)
            if not line.strip().startswith('\\'):
                sql_lines.append(line)
        
        sql_script = '\n'.join(sql_lines)
        
        # SQL 실행
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # SQL 스크립트 실행
            cursor.execute(sql_script)
            
            conn.commit()
            
            # 테이블 확인
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_name IN ('heatpump', 'groundpipe', 'elec')
                ORDER BY table_name
            """)
            
            tables = cursor.fetchall()
            cursor.close()
        
        logger.info("=" * 70)
        logger.info("✓ 데이터베이스 초기화 완료")
        logger.info("=" * 70)
        logger.info("생성된 테이블:")
        for table in tables:
            logger.info(f"  - {table[0]}")
        logger.info("=" * 70)
        
        return True
    
    except Exception as e:
        logger.error(f"✗ 데이터베이스 초기화 실패: {e}", exc_info=True)
        return False


def main():
    """메인 함수"""
    
    # 로깅 설정
    setup_logging(log_level="INFO")
    
    print("=" * 70)
    print("여주 센서 모니터링 시스템 - 데이터베이스 초기화")
    print("=" * 70)
    print()
    print("⚠️  경고: 기존 데이터가 모두 삭제됩니다!")
    print()
    
    # 사용자 확인
    response = input("계속하시겠습니까? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n취소되었습니다.")
        return 1
    
    print()
    
    # 데이터베이스 초기화
    if init_database():
        print("\n✓ 초기화가 완료되었습니다.")
        return 0
    else:
        print("\n✗ 초기화에 실패했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
