# ==============================================
# 플라스틱 함 센서 Modbus 프로토콜 정의 (동적 설정 지원)
# ==============================================
"""
플라스틱 함 센서 Modbus RTU over TCP 프로토콜

이 모듈은 플라스틱 함에 설치된 센서들의 Modbus 통신 프로토콜을 정의합니다.
각 플라스틱 함에는 온도센서 2개와 유량센서 1개가 설치되어 있습니다.

센서 구성:
- 온도센서 1: Slave ID (설정 가능), Address 0x0001, 16bit, scale=0.1
- 온도센서 2: Slave ID (설정 가능), Address 0x0001, 16bit, scale=0.1  
- 유량센서:   Slave ID (설정 가능), Address 0x0022, 32bit, scale=0.01

실제 통신 예시:
1. 온도 읽기:
   송신: 01 03 00 01 00 03 [CRC CRC]  # 3개 레지스터 읽기
   응답: 01 03 06 00 C5 F8 31 00 00 [CRC CRC]
         └─ 6바이트 데이터 = 3개 레지스터
            0x00C5 = 197 → 19.7°C (첫 번째 온도)

2. 유량 읽기:
   송신: 03 03 00 22 00 02 [CRC CRC]  # Slave ID 3
   응답: 03 03 04 00 00 00 00 [CRC CRC]
         └─ 4바이트 데이터 = 2개 레지스터 (32bit)
            0x00000000 = 0 → 0.00 L/min
"""

import logging

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 온도 센서 프로토콜
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEMPERATURE_SENSOR_PROTOCOL = {
    'address': 0x0001,      # 시작 레지스터 주소
    'count': 3,             # 읽을 레지스터 개수 (3개 = 온도1, 온도2, 온도3 or 예비)
    'type': 'INT16',        # 데이터 타입 (각 레지스터는 16bit)
    'scale': 0.1,           # 스케일 (raw × 0.1 = 실제값)
    'unit': '°C',           # 단위
    'description': '온도'
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 유량 센서 프로토콜
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW_SENSOR_PROTOCOL = {
    'address': 0x0022,      # 레지스터 주소 (34번지)
    'count': 2,             # 읽을 레지스터 개수 (32bit = 2개)
    'type': 'INT32',        # 데이터 타입 (32bit 정수)
    'scale': 0.01,          # 스케일 (raw × 0.01 = 실제값)
    'unit': 'L/min',        # 단위
    'description': '유량'
}


def parse_temperature(registers: list, index: int = 0) -> float:
    """
    온도 센서 데이터 파싱
    
    3개의 레지스터를 읽을 수 있으므로 index로 원하는 온도를 선택합니다.
    
    Args:
        registers: Modbus 응답 레지스터 리스트 (16bit 값들)
        index: 읽을 온도 인덱스 (0=첫번째, 1=두번째, 2=세번째)
        
    Returns:
        float: 온도 (°C)
        None: 파싱 실패 시
        
    Example:
        # 응답: 01 03 06 00 C5 F8 31 00 00 [CRC]
        # registers = [0x00C5, 0xF831, 0x0000]
        >>> temp1 = parse_temperature(registers, index=0)  # 0x00C5 = 197 → 19.7°C
        >>> print(temp1)
        19.7
    """
    # 레지스터 개수 확인
    if not registers or len(registers) <= index:
        logger.error(f"온도 센서 데이터 파싱 실패: 레지스터 부족 (index={index}, len={len(registers) if registers else 0})")
        return None
    
    try:
        # index 위치의 16bit 값 추출
        raw_value = registers[index]
        
        # 부호 처리 (signed 16bit)
        # 만약 값이 0x8000 이상이면 음수로 변환
        if raw_value >= 0x8000:
            raw_value -= 0x10000
        
        # 스케일 적용 (0.1을 곱함)
        temperature = raw_value * TEMPERATURE_SENSOR_PROTOCOL['scale']
        
        logger.debug(
            f"온도 파싱 [index={index}]: "
            f"raw=0x{registers[index]:04X} ({registers[index]}) → {temperature}°C"
        )
        
        return round(temperature, 2)
        
    except Exception as e:
        logger.error(f"온도 센서 데이터 파싱 오류: {e}", exc_info=True)
        return None


def parse_flow(registers: list) -> float:
    """
    유량 센서 데이터 파싱
    
    2개의 레지스터(32bit)를 조합하여 유량 값을 계산합니다.
    
    Args:
        registers: Modbus 응답 레지스터 (32bit = 2개 레지스터)
        
    Returns:
        float: 유량 (L/min)
        None: 파싱 실패 시
        
    Example:
        # 응답: 03 03 04 FE C6 00 07 [CRC]
        # registers = [0xFEC6, 0x0007]
        >>> flow = parse_flow(registers)
        >>> print(flow)
        5239.74
        
        # 응답: 03 03 04 00 00 00 00 [CRC]  (유량 없음)
        # registers = [0x0000, 0x0000]
        >>> flow = parse_flow(registers)
        >>> print(flow)
        0.0
    """
    # 레지스터 개수 확인
    if not registers or len(registers) < 2:
        logger.error(f"유량 센서 데이터 파싱 실패: 레지스터 부족 (len={len(registers) if registers else 0})")
        return None
    
    try:
        # 32bit 값 추출 (Big Endian)
        # Modbus는 레지스터 순서가 [상위 16bit, 하위 16bit]
        high_word = registers[0]  # 상위 16bit (예: 0xFEC6)
        low_word = registers[1]   # 하위 16bit (예: 0x0007)
        
        # 32bit로 합치기: (하위 << 16) | 상위
        # 0x0007FEC6 = (0x0007 << 16) | 0xFEC6
        raw_value = (low_word << 16) | high_word
        
        # 스케일 적용 (0.01을 곱함)
        # 523974 × 0.01 = 5239.74 L/min
        flow_rate = raw_value * FLOW_SENSOR_PROTOCOL['scale']
        
        logger.debug(
            f"유량 파싱: "
            f"raw=0x{high_word:04X}{low_word:04X} ({raw_value}) → {flow_rate} L/min"
        )
        
        return round(flow_rate, 2)
        
    except Exception as e:
        logger.error(f"유량 센서 데이터 파싱 오류: {e}", exc_info=True)
        return None


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """
    프로토콜 파싱 테스트
    
    실행: python src/sensors/box/protocols.py
    """
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 70)
    print("플라스틱 함 센서 프로토콜 테스트")
    print("=" * 70)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 온도 센서 파싱 테스트 (실제 통신 데이터)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 1] 온도 센서 파싱 (실제 통신 데이터)")
    print("응답: 01 03 06 00 C5 F8 31 00 00 [CRC]")
    
    # 실제 응답에서 데이터 부분만 추출
    # 00 C5, F8 31, 00 00 → 3개 레지스터
    temp_registers = [0x00C5, 0xF831, 0x0000]
    
    temp1 = parse_temperature(temp_registers, index=0)
    temp2 = parse_temperature(temp_registers, index=1)
    temp3 = parse_temperature(temp_registers, index=2)
    
    print(f"✓ 온도1 (index=0): {temp1}°C")
    print(f"✓ 온도2 (index=1): {temp2}°C")
    print(f"✓ 온도3 (index=2): {temp3}°C")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 유량 센서 파싱 테스트 (실제 통신 데이터)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 2] 유량 센서 파싱 (실제 통신 데이터)")
    print("응답: 03 03 04 00 00 00 00 [CRC]")
    
    # 실제 응답에서 데이터 부분만 추출
    # 00 00, 00 00 → 2개 레지스터
    flow_registers = [0x0000, 0x0000]
    flow_rate = parse_flow(flow_registers)
    
    print(f"✓ 유량: {flow_rate} L/min (유량 없음)")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 추가 테스트 케이스
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 3] 다양한 온도 값")
    test_cases_temp = [
        ([0x0000, 0x0000, 0x0000], 0, 0.0),       # 0
        ([0x00C8, 0x0000, 0x0000], 0, 20.0),      # 200 → 20.0°C
        ([0x0190, 0x0000, 0x0000], 0, 40.0),      # 400 → 40.0°C
        ([0xFF9C, 0x0000, 0x0000], 0, -10.0),     # -100 → -10.0°C
    ]
    
    for registers, index, expected in test_cases_temp:
        result = parse_temperature(registers, index)
        status = "✓" if result == expected else "✗"
        print(f"  {status} 0x{registers[index]:04X} → {result}°C (예상: {expected}°C)")
    
    print("\n[테스트 4] 다양한 유량 값")
    test_cases_flow = [
        ([0x0000, 0x0000], 0.0),           # 0
        ([0x03E8, 0x0000], 10.0),          # 1000 → 10.0 L/min
        ([0xFEC6, 0x0007], 5239.74),       # 523974 → 5239.74 L/min
    ]
    
    for registers, expected in test_cases_flow:
        result = parse_flow(registers)
        status = "✓" if result == expected else "✗"
        print(f"  {status} 0x{registers[0]:04X}{registers[1]:04X} → {result} L/min (예상: {expected} L/min)")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
