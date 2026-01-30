# ==============================================
# 환경 설정 관리 모듈 (수정본)
# ==============================================
"""
.env 파일에서 환경 변수를 읽어서 Config 객체로 제공
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """애플리케이션 설정 클래스"""
    
    def __init__(self):
        """초기화: .env 파일 로드 및 설정값 파싱"""
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # .env 파일 경로 찾기
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"✓ 환경 설정 로드: {env_path}")
        else:
            logger.warning(f"⚠ .env 파일 없음: {env_path}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 데이터베이스 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', '5432'))
        self.db_name = os.getenv('DB_NAME', 'sensor_yeoju')
        self.db_user = os.getenv('DB_USER', 'postgres')
        self.db_password = os.getenv('DB_PASSWORD', '1234')
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 히트펌프 센서 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.heatpump_count = int(os.getenv('HEATPUMP_COUNT', '4'))
        
        # 센서 Slave ID (온도1, 온도2, 유량)
        self.sensor_temp1_slave_id = int(os.getenv('SENSOR_TEMP1_SLAVE_ID', '1'))
        self.sensor_temp2_slave_id = int(os.getenv('SENSOR_TEMP2_SLAVE_ID', '2'))
        self.sensor_flow_slave_id = int(os.getenv('SENSOR_FLOW_SLAVE_ID', '3'))
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 지중배관 센서 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.groundpipe_count = int(os.getenv('GROUNDPIPE_COUNT', '10'))
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 전력량계 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 전력량계 IP (모두 동일)
        self.power_meter_ip = os.getenv('POWER_METER_IP', '192.168.1.200')
        
        # 전력량계 개수
        self.power_meter_count = int(os.getenv('POWER_METER_COUNT', '11'))
        
        # 시작 Slave ID
        self.power_meter_start_slave_id = int(os.getenv('POWER_METER_START_SLAVE_ID', '1'))
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Modbus TCP 공통 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.modbus_tcp_port = int(os.getenv('MODBUS_TCP_PORT', '8899'))
        self.modbus_tcp_timeout = int(os.getenv('MODBUS_TCP_TIMEOUT', '3'))
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 데이터 수집 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL', '60'))
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 로깅 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file_path = os.getenv('LOG_FILE_PATH', 'logs/app.log')
        self.log_max_bytes = int(os.getenv('LOG_MAX_BYTES', '10485760'))
        self.log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 애플리케이션 정보
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.app_name = os.getenv('APP_NAME', '여주 센서 모니터링 시스템')
        self.app_version = os.getenv('APP_VERSION', '1.0.0')
        self.project_root = project_root
    
    def get_db_connection_string(self) -> str:
        """PostgreSQL 연결 문자열 생성"""
        return (
            f"host={self.db_host} "
            f"port={self.db_port} "
            f"dbname={self.db_name} "
            f"user={self.db_user} "
            f"password={self.db_password}"
        )
    
    def print_config(self):
        """현재 설정 내용 출력"""
        print("=" * 70)
        print("현재 환경 설정")
        print("=" * 70)
        
        print("\n[애플리케이션]")
        print(f"  이름    : {self.app_name}")
        print(f"  버전    : {self.app_version}")
        
        print("\n[데이터베이스]")
        print(f"  Host    : {self.db_host}:{self.db_port}")
        print(f"  Database: {self.db_name}")
        print(f"  User    : {self.db_user}")
        print(f"  Password: {'*' * len(self.db_password)}")
        
        print("\n[히트펌프]")
        print(f"  개수          : {self.heatpump_count}대")
        print(f"  온도1 Slave ID: {self.sensor_temp1_slave_id}")
        print(f"  온도2 Slave ID: {self.sensor_temp2_slave_id}")
        print(f"  유량 Slave ID : {self.sensor_flow_slave_id}")
        
        print("\n[지중배관]")
        print(f"  개수          : {self.groundpipe_count}대")
        
        print("\n[전력량계]")
        print(f"  IP 주소       : {self.power_meter_ip}")
        print(f"  개수          : {self.power_meter_count}개")
        print(f"  시작 Slave ID : {self.power_meter_start_slave_id}")
        
        print("\n[Modbus TCP]")
        print(f"  포트          : {self.modbus_tcp_port}")
        print(f"  타임아웃      : {self.modbus_tcp_timeout}초")
        
        print("\n[데이터 수집]")
        print(f"  수집 주기     : {self.collection_interval}초")
        
        print("\n[로깅]")
        print(f"  레벨          : {self.log_level}")
        print(f"  파일 경로     : {self.log_file_path}")
        
        print("\n" + "=" * 70)


# 싱글톤 패턴
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Config 싱글톤 인스턴스 반환"""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config()
    
    return _config_instance


if __name__ == "__main__":
    config = get_config()
    config.print_config()
