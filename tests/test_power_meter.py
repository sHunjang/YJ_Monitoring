# ==============================================
# 전력량계 Reader 테스트
# ==============================================
"""
PowerMeterReader 테스트

실행: python tests/test_power_meter.py

주의: 실제 전력량계가 연결되어 있어야 합니다!
"""

import sys
from pathlib import Path

# 프로젝트 루트의 src 폴더 추가
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from core.logging_config import setup_logging
from sensors.power.reader import PowerMeterReader

# 로깅 설정
setup_logging(log_level="DEBUG")

print("=" * 70)
print("PowerMeterReader 테스트 (실제 장비)")
print("=" * 70)

# 테스트 설정 (실제 통신 데이터 기반)
test_ip = "192.168.0.82"
test_port = 8899

# 전력량계 목록
test_meters = [
    {
        'device_id': 'Total',
        'name': '전체 전력량',
        'slave_id': 1,
        'enabled': True
    },
    {
        'device_id': 'HP_1',
        'name': '히트펌프_1',
        'slave_id': 8,
        'enabled': False  # 테스트로 비활성화
    },
]

print(f"\n테스트 IP: {test_ip}:{test_port}")
print(f"전력량계 개수: {len(test_meters)}개")
print("\n⚠️  실제 전력량계가 연결되어 있어야 테스트가 성공합니다!")

# Reader 생성
reader = PowerMeterReader(
    ip=test_ip,
    port=test_port,
    meters=test_meters
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 연결 확인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[테스트 1] 연결 확인")
if reader.is_connected():
    print("✓ 연결됨")
else:
    print("ℹ️  연결 시도 중...")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 개별 전력량계 읽기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[테스트 2] 개별 전력량계 읽기")

for meter in test_meters:
    device_id = meter['device_id']
    slave_id = meter['slave_id']
    enabled = meter.get('enabled', True)
    
    if not enabled:
        print(f"\n  {device_id} (Slave {slave_id}):")
        print(f"    ⊘ 비활성화됨")
        continue
    
    print(f"\n  {device_id} (Slave {slave_id}):")
    energy = reader.read_meter(device_id, slave_id)
    
    if energy is not None:
        print(f"    ✓ {energy} kWh")
    else:
        print(f"    ✗ 읽기 실패")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 모든 전력량계 읽기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[테스트 3] 모든 전력량계 읽기")
data = reader.read_all_meters()

print("\n  읽기 결과:")
for device_id, energy in data.items():
    if energy is not None:
        print(f"    ✓ {device_id}: {energy} kWh")
    else:
        print(f"    ✗ {device_id}: 읽기 실패")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 반복 읽기 (3회)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[테스트 4] 반복 읽기 (3회)")

import time
for i in range(3):
    print(f"\n  #{i+1}회:")
    data = reader.read_all_meters()
    
    for device_id, energy in data.items():
        if energy is not None:
            print(f"    {device_id}: {energy} kWh")
        else:
            print(f"    {device_id}: 실패")
    
    # 다음 읽기까지 대기
    if i < 2:
        time.sleep(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 전력량계 목록 업데이트 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[테스트 5] 전력량계 목록 업데이트")

print(f"  현재 전력량계: {reader.get_meter_count()}개")
print(f"  활성화된 전력량계: {reader.get_enabled_meter_count()}개")

# HP_1 활성화
updated_meters = [
    {'device_id': 'Total', 'slave_id': 1, 'enabled': True},
    {'device_id': 'HP_1', 'slave_id': 8, 'enabled': True},  # 활성화
]

reader.update_meters(updated_meters)

print(f"  업데이트 후 전력량계: {reader.get_meter_count()}개")
print(f"  활성화된 전력량계: {reader.get_enabled_meter_count()}개")

# 다시 읽기
print("\n  업데이트 후 읽기:")
data = reader.read_all_meters()
for device_id, energy in data.items():
    if energy is not None:
        print(f"    ✓ {device_id}: {energy} kWh")
    else:
        print(f"    ✗ {device_id}: 실패")

print("\n" + "=" * 70)
print("✓ 테스트 완료")
print("=" * 70)
