# ==============================================
# 플라스틱 함 센서 데이터 읽기 모듈
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
    플라스틱 함 센서 데이터 읽기
    온도센서 2개 + 유량센서 1개 (Modbus RTU over TCP)
    """

    def __init__(self, device_id: str, ip: str, port: int = 8899,
                 temp1_slave_id: int = 1, temp2_slave_id: int = 2, flow_slave_id: int = 3):
        self.device_id = device_id
        self.ip = ip
        self.port = port
        self.temp1_slave_id = temp1_slave_id
        self.temp2_slave_id = temp2_slave_id
        self.flow_slave_id = flow_slave_id
        self.modbus_manager = ModbusTcpManager.get_instance()
        logger.info(f"BoxSensorReader 초기화: {device_id} ({ip}:{port})")

    def update_slave_ids(self, temp1_slave_id: int, temp2_slave_id: int, flow_slave_id: int):
        self.temp1_slave_id = temp1_slave_id
        self.temp2_slave_id = temp2_slave_id
        self.flow_slave_id = flow_slave_id

    def is_connected(self) -> bool:
        return self.modbus_manager.is_connected(self.ip, self.port)

    def _read_temperature(self, slave_id: int) -> Optional[float]:
        try:
            client = self.modbus_manager.get_client(self.ip, self.port)
            if not client:
                return None
            with self.modbus_manager.get_lock(self.ip, self.port):
                result = client.read_holding_registers(
                    address=TEMPERATURE_SENSOR_PROTOCOL['address'],
                    count=TEMPERATURE_SENSOR_PROTOCOL['count'],
                    slave=slave_id
                )
            if result.isError():
                logger.warning(f"[{self.device_id}] 온도 읽기 오류 (Slave {slave_id}): {result}")
                return None
            return parse_temperature(result.registers, index=0)
        except Exception as e:
            logger.error(f"[{self.device_id}] 온도 읽기 예외 (Slave {slave_id}): {e}", exc_info=True)
            return None

    def read_temperature_1(self) -> Optional[float]:
        return self._read_temperature(self.temp1_slave_id)

    def read_temperature_2(self) -> Optional[float]:
        return self._read_temperature(self.temp2_slave_id)

    def read_flow(self) -> Optional[float]:
        try:
            client = self.modbus_manager.get_client(self.ip, self.port)
            if not client:
                return None
            with self.modbus_manager.get_lock(self.ip, self.port):
                result = client.read_holding_registers(
                    address=FLOW_SENSOR_PROTOCOL['address'],
                    count=FLOW_SENSOR_PROTOCOL['count'],
                    slave=self.flow_slave_id
                )
            if result.isError():
                logger.warning(f"[{self.device_id}] 유량 읽기 오류 (Slave {self.flow_slave_id}): {result}")
                return None
            return parse_flow(result.registers)
        except Exception as e:
            logger.error(f"[{self.device_id}] 유량 읽기 예외: {e}", exc_info=True)
            return None

    def read_all_sensors(self) -> Optional[Dict]:
        temp1 = self.read_temperature_1()
        temp2 = self.read_temperature_2()
        flow = self.read_flow()

        if temp1 is None and temp2 is None and flow is None:
            logger.warning(f"[{self.device_id}] 모든 센서 읽기 실패")
            return None

        data = {'input_temp': temp1, 'output_temp': temp2, 'flow': flow}
        logger.debug(f"[{self.device_id}] 센서 데이터: {data}")
        return data
