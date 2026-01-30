# ==============================================
# 플라스틱 함 센서 Reader 테스트
# ==============================================
"""
BoxSensorReader 테스트

실행: python tests/test_box_reader.py
"""

import sys
from pathlib import Path

# 프로젝트 루트의 src 폴더 추가 (import 전에!)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root / 'src'))  # ← 'src' 추가!

# 이제 import 가능
from core.logging_config import setup_logging
from sensors.box.reader import BoxSensorReader

# 로깅 설정
setup_logging(log_level="DEBUG")

print("=" * 70)
print("BoxSensorReader 테스트 (실제 장비)")
print("=" * 70)

# 테스트할 장치 정보
test_device_id = "HP_1"
test_ip = "192.168.0.81"
test_port = 8899

print(f"\n테스트 장치: {test_device_id}")
print(f"IP 주소: {test_ip}:{test_port}")
print("\n⚠️  실제 센서가 연결되어 있어야 테스트가 성공합니다!")

# Reader 생성
reader = BoxSensorReader(
    device_id=test_device_id,
    ip=test_ip,
    port=test_port
)

# 1. 연결 확인
print("\n[테스트 1] 연결 확인")
if reader.is_connected():
    print("✓ 연결됨")
else:
    print("ℹ️  연결 시도 중...")

# 2. 개별 센서 읽기
print("\n[테스트 2] 개별 센서 읽기")

print("\n  온도센서 1:")
temp1 = reader.read_temperature_1()
if temp1 is not None:
    print(f"    ✓ {temp1}°C")
else:
    print(f"    ✗ 읽기 실패")

print("\n  온도센서 2:")
temp2 = reader.read_temperature_2()
if temp2 is not None:
    print(f"    ✓ {temp2}°C")
else:
    print(f"    ✗ 읽기 실패")

print("\n  유량센서:")
flow = reader.read_flow()
if flow is not None:
    print(f"    ✓ {flow} L/min")
else:
    print(f"    ✗ 읽기 실패")

# 3. 전체 센서 읽기
print("\n[테스트 3] 전체 센서 읽기")
data = reader.read_all_sensors()

if data:
    print("  ✓ 읽기 성공:")
    print(f"    입구 온도: {data['input_temp']}°C")
    print(f"    출구 온도: {data['output_temp']}°C")
    print(f"    유량: {data['flow']} L/min")
    
    if data['input_temp'] is not None and data['output_temp'] is not None:
        temp_diff = data['output_temp'] - data['input_temp']
        print(f"    온도 차이: {temp_diff}°C")
else:
    print("  ✗ 읽기 실패")

# 4. 반복 읽기 테스트 (3회)
print("\n[테스트 4] 반복 읽기 (3회)")

import time
for i in range(3):
    print(f"\n  #{i+1}회:")
    data = reader.read_all_sensors()
    
    if data:
        print(f"    입구={data['input_temp']}°C, "
              f"출구={data['output_temp']}°C, "
              f"유량={data['flow']}L/min")
    else:
        print(f"    실패")
    
    if i < 2:
        time.sleep(1)

print("\n" + "=" * 70)
print("✓ 테스트 완료")
print("=" * 70)
