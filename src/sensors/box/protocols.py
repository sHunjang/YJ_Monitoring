# ==============================================
# 플라스틱 함 센서 Modbus 프로토콜 정의
# ==============================================
import logging

logger = logging.getLogger(__name__)

TEMPERATURE_SENSOR_PROTOCOL = {
    'address': 0x0001, 'count': 3, 'type': 'INT16', 'scale': 0.1, 'unit': '°C', 'description': '온도'
}

FLOW_SENSOR_PROTOCOL = {
    'address': 0x0022, 'count': 2, 'type': 'INT32', 'scale': 1, 'unit': 'L', 'description': '유량'
}


def parse_temperature(registers: list, index: int = 0):
    if not registers or len(registers) <= index:
        logger.error(f"온도 센서 데이터 파싱 실패: 레지스터 부족 (index={index})")
        return None
    try:
        raw_value = registers[index]
        if raw_value >= 0x8000:
            raw_value -= 0x10000
        temperature = raw_value * TEMPERATURE_SENSOR_PROTOCOL['scale']
        logger.debug(f"온도 파싱 [index={index}]: raw=0x{registers[index]:04X} → {temperature}°C")
        return round(temperature, 1)
    except Exception as e:
        logger.error(f"온도 센서 데이터 파싱 오류: {e}", exc_info=True)
        return None


def parse_flow(registers: list):
    if not registers or len(registers) < 2:
        logger.error(f"유량 센서 데이터 파싱 실패: 레지스터 부족")
        return None
    try:
        high_word = registers[0]
        low_word = registers[1]
        raw_value = (low_word << 16) | high_word
        flow_rate = raw_value * FLOW_SENSOR_PROTOCOL['scale']
        logger.debug(f"유량 파싱: raw=0x{high_word:04X}{low_word:04X} ({raw_value}) → {flow_rate} L")
        return int(flow_rate)
    except Exception as e:
        logger.error(f"유량 센서 데이터 파싱 오류: {e}", exc_info=True)
        return None
