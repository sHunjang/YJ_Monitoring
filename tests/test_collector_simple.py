# ==============================================
# Collector 통합 테스트 (HP_1 완전 데이터)
# ==============================================
"""
HP_1 완전 데이터 수집 테스트

- 플라스틱 함 (192.168.0.81:8899): 온도(입구/출구) + 유량
- 전력량계 (192.168.0.82:8899, Slave 1): 전력량

실행: python tests/test_collector_simple.py
"""

import sys
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from core.logging_config import setup_logging
from core.database import test_db_connection, initialize_connection_pool
from sensors.box.collector import BoxSensorCollector
from sensors.power.reader import PowerMeterReader

setup_logging(log_level="INFO")

print("=" * 70)
print("HP_1 완전 데이터 수집 테스트")
print("=" * 70)
print("\nHP_1 데이터 구성:")
print("  - 온도/유량: 192.168.0.81:8899 (Slave 1,2,3)")
print("  - 전력량:   192.168.0.82:8899 (Slave 1)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 데이터베이스 연결
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[1단계] 데이터베이스 연결")
initialize_connection_pool()

if not test_db_connection():
    print("✗ 데이터베이스 연결 실패")
    sys.exit(1)

print("✓ 데이터베이스 연결 성공")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 전력량 데이터 수집
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[2단계] HP_1 전력량 수집")
print("  IP: 192.168.0.82:8899")
print("  Slave ID: 1")

# 전력량계 Reader 생성 (HP_1만)
power_reader = PowerMeterReader(
    ip='192.168.0.82',
    port=8899,
    meters=[
        {'device_id': 'HP_1', 'slave_id': 1, 'enabled': True}
    ]
)

print("\n전력량 읽기 중...")
power_energy = power_reader.read_meter('HP_1', slave_id=1)

if power_energy is not None:
    print(f"✓ HP_1 전력량: {power_energy} kWh")
    power_data = {'HP_1': power_energy}
else:
    print("✗ HP_1 전력량 읽기 실패 (전력량 없이 저장됩니다)")
    power_data = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 온도/유량 데이터 수집 + 데이터베이스 저장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[3단계] HP_1 온도/유량 수집 및 통합 저장")
print("  IP: 192.168.0.81:8899")
print("  Slave ID: 1(온도1), 2(온도2), 3(유량)")

collector = BoxSensorCollector()

print("\n온도/유량 읽기 및 저장 중...")
success = collector.collect_heatpump('HP_1', power_meter_data=power_data)

if success:
    print("✓ HP_1 완전 데이터 수집 및 저장 성공!")
else:
    print("✗ HP_1 데이터 수집 실패")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 데이터베이스 확인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[4단계] 데이터베이스 확인")

import psycopg2
from core.config import get_config

try:
    config = get_config()
    
    # PostgreSQL 연결
    conn = psycopg2.connect(
        host=config.db_host,
        port=config.db_port,
        database=config.db_name,
        user=config.db_user,
        password=config.db_password
    )
    cursor = conn.cursor()
    
    # 최근 데이터 1개
    cursor.execute(
        "SELECT device_id, timestamp, input_temp, output_temp, flow, energy "
        "FROM heatpump WHERE device_id = 'HP_1' ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    
    if row:
        device_id, timestamp, input_temp, output_temp, flow, energy = row
        print("\n✓ HP_1 최근 데이터 (완전):")
        print(f"  시간:       {timestamp}")
        print(f"  입구 온도:  {input_temp}°C")
        print(f"  출구 온도:  {output_temp}°C")
        print(f"  유량:       {flow} L/min")
        print(f"  전력량:     {energy} kWh")
        
        # 온도 차이 계산
        if input_temp and output_temp:
            temp_diff = output_temp - input_temp
            print(f"  온도 차이:  {temp_diff}°C")
    else:
        print("\n⚠️  데이터 없음")
    
    # 최근 5개 데이터
    cursor.execute(
        "SELECT device_id, timestamp, input_temp, output_temp, flow, energy "
        "FROM heatpump WHERE device_id = 'HP_1' ORDER BY timestamp DESC LIMIT 5"
    )
    rows = cursor.fetchall()
    
    if len(rows) > 1:
        print(f"\n최근 5개 데이터:")
        print(f"{'시간':<20} {'입구(°C)':<10} {'출구(°C)':<10} {'유량(L/min)':<12} {'전력량(kWh)':<12}")
        print("-" * 70)
        for row in rows:
            device_id, timestamp, input_temp, output_temp, flow, energy = row
            energy_str = f"{energy:.2f}" if energy else "N/A"
            timestamp_str = str(timestamp).split('.')[0]  # 밀리초 제거
            print(f"{timestamp_str:<20} "
                  f"{input_temp:<10.1f} "
                  f"{output_temp:<10.1f} "
                  f"{flow:<12.1f} "
                  f"{energy_str:<12}")
    
    # 전체 개수
    cursor.execute("SELECT COUNT(*) FROM heatpump WHERE device_id = 'HP_1'")
    count = cursor.fetchone()[0]
    print(f"\nHP_1 총 데이터: {count}개")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"\n✗ 오류: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✓ 테스트 완료")
print("=" * 70)

# 다음 단계 안내
print("\n💡 다음 단계:")
print("  1. 여러 번 실행해서 데이터 누적 확인")
print("  2. 다른 히트펌프(HP_2, HP_3, HP_4) 설정")
print("  3. Service 테스트 (자동 주기 수집)")
print("  4. GUI 실행 테스트")
