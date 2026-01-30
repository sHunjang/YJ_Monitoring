# ==============================================
# 전력량계 Modbus 프로토콜 정의
# ==============================================
"""
전력량계 Modbus RTU over TCP 프로토콜

이 모듈은 전력량계의 Modbus 통신 프로토콜을 정의합니다.
전력량계는 누적 전력량(kWh)을 32bit Float 형식으로 제공합니다.

실제 통신 예시:
- IP: 192.168.0.82
- 송신: 01 03 04 04 00 02 [CRC CRC]
  └─ Slave ID 1, Function 03(Read Holding Registers)
     Address 0x0404, Count 2 (32bit = 2개 레지스터)
     
- 응답: 01 03 04 00 00 00 00 [CRC CRC]
  └─ 4바이트 데이터 = 0x00000000
     Float32로 파싱 → 0.0 kWh
"""

import logging

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 전력량계 프로토콜
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POWER_METER_PROTOCOL = {
    'address': 0x0404,      # 레지스터 주소 (실제 통신에서 확인됨)
    'count': 2,             # 읽을 레지스터 개수 (32bit Float = 2개)
    'type': 'FLOAT32',      # 데이터 타입 (32bit 부동소수점)
    'unit': 'kWh',          # 단위
    'description': '누적 전력량'
}


def parse_power_meter(registers: list) -> float:
    """
    전력량계 데이터 파싱
    
    2개의 레지스터(32bit)를 IEEE 754 Float32 형식으로 파싱합니다.
    
    Args:
        registers: Modbus 응답 레지스터 (32bit Float = 2개 레지스터)
        
    Returns:
        float: 누적 전력량 (kWh)
        None: 파싱 실패 시
        
    Example:
        # 응답: 01 03 04 00 00 00 00 [CRC]
        # registers = [0x0000, 0x0000]
        >>> energy = parse_power_meter(registers)
        >>> print(energy)
        0.0
        
        # 다른 예시 (123.45 kWh)
        # registers = [0x42F6, 0xE666]  # Float32 encoding
        >>> energy = parse_power_meter(registers)
        >>> print(energy)
        123.45
    """
    # 레지스터 개수 확인
    if not registers or len(registers) < 2:
        logger.error(f"전력량계 데이터 파싱 실패: 레지스터 부족 (len={len(registers) if registers else 0})")
        return None
    
    try:
        # 32bit Float 파싱 (Big Endian)
        import struct
        
        # 레지스터는 [상위 16bit, 하위 16bit] 순서
        high_word = registers[0]  # 상위 워드
        low_word = registers[1]   # 하위 워드
        
        # Big Endian으로 32bit float 구성
        # struct.pack('>HH', ...)는 2개의 16bit를 Big Endian으로 패킹
        # struct.unpack('>f', ...)는 32bit float로 언패킹
        byte_array = struct.pack('>HH', high_word, low_word)
        energy = struct.unpack('>f', byte_array)[0]
        
        logger.debug(
            f"전력량 파싱: "
            f"raw=0x{high_word:04X}{low_word:04X} → {energy} kWh"
        )
        
        # 음수 값이면 0으로 처리 (전력량은 항상 양수)
        if energy < 0:
            logger.warning(f"전력량이 음수입니다: {energy} kWh → 0.0 kWh")
            energy = 0.0
        
        return round(energy, 2)
        
    except Exception as e:
        logger.error(f"전력량계 데이터 파싱 오류: {e}", exc_info=True)
        return None


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """
    전력량계 프로토콜 파싱 테스트
    
    실행: python src/sensors/power/protocols.py
    """
    import logging
    import struct
    
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 70)
    print("전력량계 프로토콜 테스트")
    print("=" * 70)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 실제 통신 데이터 파싱
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 1] 실제 통신 데이터 파싱")
    print("응답: 01 03 04 00 00 00 00 [CRC]")
    
    # 실제 응답 데이터
    registers = [0x0000, 0x0000]
    energy = parse_power_meter(registers)
    
    print(f"✓ 전력량: {energy} kWh")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 다양한 전력량 값 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 2] 다양한 전력량 값")
    
    test_values = [0.0, 123.45, 1000.5, 9999.99]
    
    for test_value in test_values:
        # Float을 레지스터로 인코딩
        byte_array = struct.pack('>f', test_value)
        high_word, low_word = struct.unpack('>HH', byte_array)
        registers = [high_word, low_word]
        
        # 파싱
        parsed = parse_power_meter(registers)
        
        # 비교 (부동소수점 오차 허용)
        match = abs(parsed - test_value) < 0.01 if parsed is not None else False
        status = "✓" if match else "✗"
        
        print(f"  {status} {test_value} kWh → [0x{high_word:04X}, 0x{low_word:04X}] → {parsed} kWh")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
