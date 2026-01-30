# ==============================================
# Service 테스트 (자동 주기 수집)
# ==============================================
"""
DataCollectionService 테스트

30초마다 자동으로 센서 데이터를 수집하고 저장합니다.

실행: python tests/test_service.py

종료: Ctrl+C
"""

import sys
from pathlib import Path
import time
import signal

# 프로젝트 루트의 src 폴더 추가
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from core.logging_config import setup_logging
from core.database import test_db_connection, initialize_connection_pool
from services.data_collection_service import DataCollectionService

# 로깅 설정
setup_logging(log_level="INFO")

print("=" * 70)
print("Data Collection Service 테스트")
print("=" * 70)

# 종료 플래그
running = True

def signal_handler(sig, frame):
    """Ctrl+C 핸들러"""
    global running
    print("\n\n" + "=" * 70)
    print("종료 신호 받음 (Ctrl+C)")
    print("=" * 70)
    running = False

# Ctrl+C 핸들러 등록
signal.signal(signal.SIGINT, signal_handler)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 데이터베이스 연결 확인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[1단계] 데이터베이스 연결 확인")
initialize_connection_pool()

if not test_db_connection():
    print("✗ 데이터베이스 연결 실패")
    sys.exit(1)

print("✓ 데이터베이스 연결 성공")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Service 생성 및 시작
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[2단계] Data Collection Service 시작")
print("\n설정:")
print("  - 수집 주기: 30초")
print("  - 대상: config/box_ips.json의 모든 장치")
print("  - 전력량: config/power_meter_config.json")

# Service 생성 (파라미터 없이)
service = DataCollectionService()

print("\nService 시작 중...")
service.start()

print("\n✓ Service 시작됨!")
print("\n" + "=" * 70)
print("자동 데이터 수집 실행 중...")
print("=" * 70)
print("\n💡 안내:")
print("  - 30초마다 자동으로 데이터 수집")
print("  - 종료하려면 Ctrl+C 누르기")
print("  - 데이터베이스를 확인하여 데이터 누적 확인 가능")
print("\n" + "-" * 70)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 실행 중 상태 모니터링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
iteration = 0
start_time = time.time()

try:
    while running:
        time.sleep(5)  # 5초마다 상태 체크
        iteration += 1
        
        # 30초마다 (6번째 iteration) 상태 출력
        if iteration % 6 == 0:
            elapsed = int(time.time() - start_time)
            print(f"\n[{time.strftime('%H:%M:%S')}] Service 실행 중... (경과: {elapsed}초, Ctrl+C로 종료)")

except KeyboardInterrupt:
    print("\n\n종료 신호 받음...")

finally:
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. Service 종료
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[3단계] Service 종료 중...")
    service.stop()
    
    print("\n✓ Service 정상 종료됨")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. 최종 통계
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[4단계] 최종 통계")
    
    import psycopg2
    from core.config import get_config
    
    try:
        config = get_config()
        conn = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            database=config.db_name,
            user=config.db_user,
            password=config.db_password
        )
        cursor = conn.cursor()
        
        # 히트펌프 데이터 개수
        cursor.execute("SELECT COUNT(*) FROM heatpump")
        hp_count = cursor.fetchone()[0]
        
        # 지중배관 데이터 개수
        cursor.execute("SELECT COUNT(*) FROM groundpipe")
        gp_count = cursor.fetchone()[0]
        
        # 전력량계 데이터 개수
        cursor.execute("SELECT COUNT(*) FROM elec")
        elec_count = cursor.fetchone()[0]
        
        print(f"\n저장된 데이터:")
        print(f"  히트펌프:  {hp_count}개")
        print(f"  지중배관:  {gp_count}개")
        print(f"  전력량계:  {elec_count}개")
        print(f"  총합:      {hp_count + gp_count + elec_count}개")
        
        # 최근 수집 시간
        cursor.execute(
            "SELECT MAX(timestamp) FROM ("
            "  SELECT MAX(timestamp) as timestamp FROM heatpump "
            "  UNION ALL SELECT MAX(timestamp) FROM groundpipe "
            "  UNION ALL SELECT MAX(timestamp) FROM elec"
            ") t"
        )
        last_time = cursor.fetchone()[0]
        
        if last_time:
            print(f"\n최근 수집 시간: {last_time}")
        
        # HP_1 최근 3개 데이터
        cursor.execute(
            "SELECT timestamp, input_temp, output_temp, flow, energy "
            "FROM heatpump WHERE device_id = 'HP_1' "
            "ORDER BY timestamp DESC LIMIT 3"
        )
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nHP_1 최근 3개 데이터:")
            print(f"{'시간':<20} {'입구(°C)':<10} {'출구(°C)':<10} {'유량':<10} {'전력량':<10}")
            print("-" * 60)
            for row in rows:
                timestamp, input_temp, output_temp, flow, energy = row
                ts = str(timestamp).split('.')[0]
                energy_str = f"{energy:.1f}" if energy is not None else "N/A"
                print(f"{ts:<20} {input_temp:<10.1f} {output_temp:<10.1f} {flow:<10.1f} {energy_str:<10}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n통계 조회 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
