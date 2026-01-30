# ==============================================
# GUI 실행 파일
# ==============================================
"""
여주 센서 모니터링 GUI 실행

실행:
    python src/main_gui.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from PyQt6.QtWidgets import QApplication

from core.logging_config import setup_logging
from core.config import get_config
from core.database import initialize_connection_pool, test_db_connection
from ui.main_window import MainWindow


def main():
    """메인 함수"""
    
    # 로깅 설정
    setup_logging(log_level="INFO")
    
    # 설정 로드
    config = get_config()
    
    print("=" * 70)
    print(f"{config.app_name} GUI v{config.app_version}")
    print("=" * 70)
    
    # 데이터베이스 연결
    try:
        initialize_connection_pool()
        
        if not test_db_connection():
            print("✗ 데이터베이스 연결 실패")
            print("다음을 확인하세요:")
            print("  1. PostgreSQL이 실행 중인지")
            print("  2. .env 파일의 DB 설정이 올바른지")
            print("  3. python src/core/init_db.py를 실행했는지")
            return 1
        
        print("✓ 데이터베이스 연결 성공")
        
    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")
        return 1
    
    # PyQt6 애플리케이션 시작
    app = QApplication(sys.argv)
    
    # 메인 윈도우 생성
    window = MainWindow()
    window.show()
    
    print("=" * 70)
    print("GUI 실행 중...")
    print("=" * 70)
    
    # 이벤트 루프 시작
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
