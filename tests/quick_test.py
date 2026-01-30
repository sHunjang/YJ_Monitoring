# ==============================================
# 빠른 기능 테스트
# ==============================================
"""
실제 장비 없이 기본 기능 테스트

실행: python tests/quick_test.py
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

print("=" * 70)
print("고성 센서 모니터링 시스템 - 빠른 테스트")
print("=" * 70)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 설정 로드 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[1/6] 설정 로드 테스트")
try:
    from core.config import get_config
    config = get_config()
    print(f"  ✓ 앱 이름: {config.app_name}")
    print(f"  ✓ DB: {config.db_name}")
    print(f"  ✓ 수집 주기: {config.collection_interval}초")
except Exception as e:
    print(f"  ✗ 실패: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 설정 파일 읽기 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[2/6] 설정 파일 읽기 테스트")
try:
    from services.config_service import ConfigService
    service = ConfigService()
    
    heatpumps = service.get_heatpump_ips()
    groundpipes = service.get_groundpipe_ips()
    power_meters = service.get_power_meters()
    
    print(f"  ✓ 히트펌프: {len(heatpumps)}개")
    print(f"  ✓ 지중배관: {len(groundpipes)}개")
    print(f"  ✓ 전력량계: {len(power_meters)}개")
except Exception as e:
    print(f"  ✗ 실패: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 프로토콜 파싱 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[3/6] 프로토콜 파싱 테스트")
try:
    from sensors.box.protocols import parse_temperature, parse_flow
    
    # 온도 파싱
    temp = parse_temperature([0x00AA])  # 170 → 17.0°C
    print(f"  ✓ 온도 파싱: {temp}°C (예상: 17.0)")
    
    # 유량 파싱
    flow = parse_flow([0xFEC6, 0x0007])  # 523974 → 5239.74 L/min
    print(f"  ✓ 유량 파싱: {flow} L/min (예상: 5239.74)")
    
except Exception as e:
    print(f"  ✗ 실패: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 데이터 모델 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[4/6] 데이터 모델 테스트")
try:
    from sensors.box.models import HeatpumpData
    from sensors.power.models import PowerMeterData
    
    # 히트펌프 데이터
    hp_data = HeatpumpData(
        device_id='HP_1',
        input_temp=25.5,
        output_temp=30.2,
        flow=15.3,
        energy=123.45
    )
    print(f"  ✓ 히트펌프: {hp_data.device_id}, ΔT={hp_data.get_temp_diff()}°C")
    
    # 전력량계 데이터
    pm_data = PowerMeterData(
        device_id='HP_1',
        total_energy=123.45
    )
    print(f"  ✓ 전력량계: {pm_data.device_id}, {pm_data.total_energy}kWh")
    
except Exception as e:
    print(f"  ✗ 실패: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 데이터베이스 연결 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[5/6] 데이터베이스 연결 테스트")
try:
    from core.database import test_db_connection
    
    if test_db_connection():
        print(f"  ✓ 데이터베이스 연결 성공")
    else:
        print(f"  ✗ 데이터베이스 연결 실패")
        
except Exception as e:
    print(f"  ✗ 실패: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. Modbus TCP 매니저 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[6/6] Modbus TCP 매니저 테스트")
try:
    from core.modbus_tcp_manager import ModbusTcpManager
    
    manager = ModbusTcpManager.get_instance()
    print(f"  ✓ Modbus TCP 매니저 초기화 완료")
    
except Exception as e:
    print(f"  ✗ 실패: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 완료
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n" + "=" * 70)
print("✓ 빠른 테스트 완료")
print("=" * 70)
print("\n다음 단계:")
print("  1. 실제 센서 장비 연결")
print("  2. config/box_ips.json에서 IP 주소 확인")
print("  3. python src/sensors/box/reader.py 실행")
print("  4. python src/main.py 실행")
print("=" * 70)
