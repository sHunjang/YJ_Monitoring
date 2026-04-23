# ==============================================
# 온도, 유량 센서 데이터 읽기 모듈 (안정성 강화)
# ==============================================
import logging
from typing import Optional, Dict

from sensors.box.protocols import (
    TEMPERATURE_SENSOR_PROTOCOL, FLOW_SENSOR_PROTOCOL,
    parse_temperature, parse_flow
)
from core.modbus_tcp_manager import ModbusTcpManager

logger = logging.getLogger(__name__)


class BoxSensorReader:
    """
    온도, 유량 센서 데이터 읽기
    온도센서 2개 + 유량센서 1개 (Modbus RTU over TCP)

    개선:
    - 읽기 성공/실패를 ModbusTcpManager에 리포트
      → Circuit Breaker 연동
    - 개별 센서 실패 시 다른 센서는 계속 읽기
    """

    def __init__(self, device_id: str, ip: str, port: int = 8899,
                 temp1_slave_id: int = 1, temp2_slave_id: int = 2,
                 flow_slave_id: int = 3):
        self.device_id      = device_id
        self.ip             = ip
        self.port           = port
        self.temp1_slave_id = temp1_slave_id
        self.temp2_slave_id = temp2_slave_id
        self.flow_slave_id  = flow_slave_id
        self.modbus_manager = ModbusTcpManager.get_instance()
        logger.info(f"BoxSensorReader 초기화: {device_id} ({ip}:{port})")

    def update_slave_ids(self, temp1_slave_id: int,
                         temp2_slave_id: int, flow_slave_id: int):
        self.temp1_slave_id = temp1_slave_id
        self.temp2_slave_id = temp2_slave_id
        self.flow_slave_id  = flow_slave_id

    def is_connected(self) -> bool:
        return self.modbus_manager.is_connected(self.ip, self.port)

    def _read_register(self, protocol: dict, slave_id: int,
                       parse_fn, label: str) -> Optional[float]:
        """
        레지스터 읽기 공통 메서드.
        성공/실패를 Circuit Breaker에 리포트.
        """
        try:
            client = self.modbus_manager.get_client(self.ip, self.port)
            if not client:
                # Circuit Breaker 차단 중이거나 연결 실패 — 즉시 반환
                return None

            with self.modbus_manager.get_lock(self.ip, self.port):
                result = client.read_holding_registers(
                    address=protocol['address'],
                    count=protocol['count'],
                    slave=slave_id
                )

            if result.isError():
                logger.warning(
                    f"[{self.device_id}] {label} 읽기 오류 "
                    f"(Slave {slave_id}): {result}"
                )
                self.modbus_manager.record_read_failure(self.ip, self.port)
                return None

            value = parse_fn(result.registers)
            self.modbus_manager.record_read_success(self.ip, self.port)
            return value

        except Exception as e:
            logger.error(
                f"[{self.device_id}] {label} 읽기 예외 "
                f"(Slave {slave_id}): {e}"
            )
            self.modbus_manager.record_read_failure(self.ip, self.port)
            return None

    def read_temperature_1(self) -> Optional[float]:
        return self._read_register(
            TEMPERATURE_SENSOR_PROTOCOL,
            self.temp1_slave_id,
            lambda regs: parse_temperature(regs, index=0),
            '입구온도'
        )

    def read_temperature_2(self) -> Optional[float]:
        return self._read_register(
            TEMPERATURE_SENSOR_PROTOCOL,
            self.temp2_slave_id,
            lambda regs: parse_temperature(regs, index=0),
            '출구온도'
        )

    def read_flow(self) -> Optional[float]:
        return self._read_register(
            FLOW_SENSOR_PROTOCOL,
            self.flow_slave_id,
            parse_flow,
            '유량'
        )

    def read_all_sensors(self) -> Optional[Dict]:
        """
        3개 센서 모두 읽기.
        개별 센서 실패해도 나머지는 계속 읽음.
        전부 실패한 경우에만 None 반환.
        """
        temp1 = self.read_temperature_1()
        temp2 = self.read_temperature_2()
        flow  = self.read_flow()

        if temp1 is None and temp2 is None and flow is None:
            logger.warning(f"[{self.device_id}] 모든 센서 읽기 실패")
            return None

        data = {'input_temp': temp1, 'output_temp': temp2, 'flow': flow}
        logger.debug(f"[{self.device_id}] 센서 데이터: {data}")
        return data