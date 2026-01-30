# ==============================================
# 플라스틱 함 센서 Reader 모듈 (동적 Slave ID 지원)
# ==============================================
"""
플라스틱 함 센서 데이터 읽기

이 모듈은 Modbus TCP를 통해 플라스틱 함의 센서 데이터를 읽습니다.
각 플라스틱 함에는 온도센서 2개와 유량센서 1개가 설치되어 있습니다.

하드웨어 구성:
- 온도센서 1 (Slave ID: 설정 가능, 기본값 1)
- 온도센서 2 (Slave ID: 설정 가능, 기본값 2)
- 유량센서 (Slave ID: 설정 가능, 기본값 3)

통신 설정:
- 프로토콜: Modbus TCP
- 포트: 8899 (설정 가능)
- 타임아웃: 3초

실제 통신 예시:
1. IP: 192.168.0.81, Port: 8899
2. 온도센서 1 (Slave ID 1):
   - 송신: 01 03 00 01 00 03 [CRC]  # 3개 레지스터 읽기
   - 응답: 01 03 06 00 C5 F8 31 00 00 [CRC]
   - 파싱: 0x00C5 = 197 → 19.7°C
   
3. 유량센서 (Slave ID 3):
   - 송신: 03 03 00 22 00 02 [CRC]  # 2개 레지스터 읽기
   - 응답: 03 03 04 00 00 00 00 [CRC]
   - 파싱: 0x00000000 = 0 → 0.0 L/min

사용 예:
    # 기본 Slave ID로 Reader 생성
    reader = BoxSensorReader(
        device_id='HP_1',
        ip='192.168.0.81',
        port=8899
    )
    
    # 데이터 읽기
    data = reader.read_all_sensors()
    if data:
        print(f"입구: {data['input_temp']}°C")
        print(f"출구: {data['output_temp']}°C")
        print(f"유량: {data['flow']} L/min")
"""

import logging
from typing import Optional, Dict, Any

from core.modbus_tcp_manager import ModbusTcpManager
from sensors.box.protocols import (
    TEMPERATURE_SENSOR_PROTOCOL,
    FLOW_SENSOR_PROTOCOL,
    parse_temperature,
    parse_flow
)

logger = logging.getLogger(__name__)


class BoxSensorReader:
    """
    플라스틱 함 센서 Reader
    
    하나의 플라스틱 함(IP)에 연결된 3개 센서를 읽습니다.
    Slave ID는 동적으로 설정 가능합니다.
    
    Attributes:
        device_id (str): 장치 ID (예: 'HP_1', 'GP_1')
        ip (str): IP 주소
        port (int): TCP 포트 (기본값: 8899)
        temp1_slave_id (int): 온도센서 1 Slave ID
        temp2_slave_id (int): 온도센서 2 Slave ID
        flow_slave_id (int): 유량센서 Slave ID
    """
    
    def __init__(
        self,
        device_id: str,
        ip: str,
        port: int = 8899,
        temp1_slave_id: int = 1,
        temp2_slave_id: int = 2,
        flow_slave_id: int = 3
    ):
        """
        초기화
        
        Args:
            device_id: 장치 ID (예: 'HP_1', 'GP_1')
            ip: IP 주소 (예: '192.168.0.81')
            port: TCP 포트 (기본값: 8899)
            temp1_slave_id: 온도센서 1 Slave ID (기본값: 1)
            temp2_slave_id: 온도센서 2 Slave ID (기본값: 2)
            flow_slave_id: 유량센서 Slave ID (기본값: 3)
            
        Example:
            >>> # 기본 Slave ID 사용
            >>> reader = BoxSensorReader('HP_1', '192.168.0.81')
            
            >>> # 커스텀 Slave ID 사용
            >>> reader = BoxSensorReader(
            >>>     'HP_1', '192.168.0.81',
            >>>     port=8899,
            >>>     temp1_slave_id=10,
            >>>     temp2_slave_id=11,
            >>>     flow_slave_id=12
            >>> )
        """
        self.device_id = device_id
        self.ip = ip
        self.port = port
        
        # 동적 Slave ID 설정
        self.temp1_slave_id = temp1_slave_id
        self.temp2_slave_id = temp2_slave_id
        self.flow_slave_id = flow_slave_id
        
        # Modbus TCP 매니저 (싱글톤 패턴)
        self.modbus_manager = ModbusTcpManager.get_instance()
        
        # 로거 (장치별 구분)
        self.logger = logging.getLogger(f"{__name__}.{device_id}")
        
        self.logger.debug(f"BoxSensorReader 초기화: {device_id}")
        self.logger.debug(f"  IP: {ip}:{port}")
        self.logger.debug(f"  온도1 Slave ID: {self.temp1_slave_id}")
        self.logger.debug(f"  온도2 Slave ID: {self.temp2_slave_id}")
        self.logger.debug(f"  유량 Slave ID: {self.flow_slave_id}")
    
    def read_temperature_1(self) -> Optional[float]:
        """
        온도센서 1 읽기 (입구 온도)
        
        Modbus 통신:
        - Slave ID: self.temp1_slave_id
        - Function: 03 (Read Holding Registers)
        - Address: 0x0001
        - Count: 3 (3개 레지스터 읽기)
        
        Returns:
            float: 온도 (°C)
            None: 읽기 실패 시
            
        Example:
            >>> temp = reader.read_temperature_1()
            >>> if temp is not None:
            >>>     print(f"입구 온도: {temp}°C")
        """
        return self._read_temperature(self.temp1_slave_id, "온도1 (입구)", index=0)
    
    def read_temperature_2(self) -> Optional[float]:
        """
        온도센서 2 읽기 (출구 온도)
        
        실제로는 온도센서 1과 같은 IP에서 다른 Slave ID로 읽거나,
        또는 같은 응답에서 다른 레지스터를 사용할 수 있습니다.
        
        Returns:
            float: 온도 (°C)
            None: 읽기 실패 시
        """
        return self._read_temperature(self.temp2_slave_id, "온도2 (출구)", index=0)
    
    def _read_temperature(self, slave_id: int, sensor_name: str, index: int = 0) -> Optional[float]:
        """
        온도센서 읽기 (내부 메서드)
        
        이 메서드는 실제 Modbus 통신을 수행합니다.
        
        통신 흐름:
        1. Modbus TCP 클라이언트 가져오기
        2. Lock 획득 (동시 접근 방지)
        3. Holding Register 읽기 (Function Code 03)
        4. 응답 데이터 파싱
        5. Lock 해제
        
        Args:
            slave_id: Modbus Slave ID
            sensor_name: 센서 이름 (로그용)
            index: 레지스터 인덱스 (3개 중 몇 번째를 읽을지)
            
        Returns:
            float: 온도 (°C)
            None: 읽기 실패 시
        """
        try:
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. Modbus TCP 클라이언트 가져오기
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            client = self.modbus_manager.get_client(self.ip, self.port)
            
            if not client:
                self.logger.error(f"[{self.device_id}] Modbus 연결 실패")
                return None
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. Modbus 통신 (Lock으로 보호)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with self.modbus_manager.get_lock(self.ip, self.port):
                # Holding Register 읽기
                # Function Code: 0x03
                # Address: TEMPERATURE_SENSOR_PROTOCOL['address']
                # Count: TEMPERATURE_SENSOR_PROTOCOL['count']
                result = client.read_holding_registers(
                    address=TEMPERATURE_SENSOR_PROTOCOL['address'],
                    count=TEMPERATURE_SENSOR_PROTOCOL['count'],
                    slave=slave_id
                )
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 3. 응답 확인
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                if result.isError():
                    self.logger.error(
                        f"[{self.device_id}] {sensor_name} 읽기 실패 "
                        f"(Slave ID: {slave_id}): {result}"
                    )
                    return None
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 4. 데이터 파싱
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                temperature = parse_temperature(result.registers, index=index)
                
                if temperature is not None:
                    self.logger.debug(
                        f"[{self.device_id}] {sensor_name} (Slave {slave_id}): {temperature}°C"
                    )
                
                return temperature
                
        except Exception as e:
            self.logger.error(
                f"[{self.device_id}] {sensor_name} 읽기 오류: {e}",
                exc_info=True
            )
            return None
    
    def read_flow(self) -> Optional[float]:
        """
        유량센서 읽기
        
        Modbus 통신:
        - Slave ID: self.flow_slave_id
        - Function: 03 (Read Holding Registers)
        - Address: 0x0022 (34번지)
        - Count: 2 (32bit = 2개 레지스터)
        
        Returns:
            float: 유량 (L/min)
            None: 읽기 실패 시
            
        Example:
            >>> flow = reader.read_flow()
            >>> if flow is not None:
            >>>     print(f"유량: {flow} L/min")
        """
        try:
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. Modbus TCP 클라이언트 가져오기
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            client = self.modbus_manager.get_client(self.ip, self.port)
            
            if not client:
                self.logger.error(f"[{self.device_id}] Modbus 연결 실패")
                return None
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. Modbus 통신 (Lock으로 보호)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with self.modbus_manager.get_lock(self.ip, self.port):
                # Holding Register 읽기 (32bit = 2개 레지스터)
                result = client.read_holding_registers(
                    address=FLOW_SENSOR_PROTOCOL['address'],
                    count=FLOW_SENSOR_PROTOCOL['count'],
                    slave=self.flow_slave_id
                )
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 3. 응답 확인
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                if result.isError():
                    self.logger.error(
                        f"[{self.device_id}] 유량센서 읽기 실패 "
                        f"(Slave ID: {self.flow_slave_id}): {result}"
                    )
                    return None
                
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 4. 데이터 파싱
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                flow_rate = parse_flow(result.registers)
                
                if flow_rate is not None:
                    self.logger.debug(
                        f"[{self.device_id}] 유량 (Slave {self.flow_slave_id}): {flow_rate} L/min"
                    )
                
                return flow_rate
                
        except Exception as e:
            self.logger.error(
                f"[{self.device_id}] 유량센서 읽기 오류: {e}",
                exc_info=True
            )
            return None
    
    def read_all_sensors(self) -> Optional[Dict[str, float]]:
        """
        모든 센서 읽기 (온도 2개 + 유량 1개)
        
        데이터 수집 순서:
        1. 온도센서 1 (입구 온도)
        2. 온도센서 2 (출구 온도)
        3. 유량센서
        
        부분 실패 허용:
        - 일부 센서가 실패해도 다른 센서는 계속 읽습니다
        - 모든 센서가 실패하면 None을 반환합니다
        
        Returns:
            dict: {
                'input_temp': float,   # 입구 온도 (온도1)
                'output_temp': float,  # 출구 온도 (온도2)
                'flow': float          # 유량
            }
            None: 모든 센서 읽기 실패 시
            
        Example:
            >>> data = reader.read_all_sensors()
            >>> if data:
            >>>     print(f"입구: {data['input_temp']}°C")
            >>>     print(f"출구: {data['output_temp']}°C")
            >>>     print(f"유량: {data['flow']} L/min")
            >>>     print(f"온도차: {data['output_temp'] - data['input_temp']}°C")
        """
        try:
            self.logger.debug(f"[{self.device_id}] 센서 데이터 읽기 시작")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. 온도센서 1 읽기 (입구 온도)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            input_temp = self.read_temperature_1()
            if input_temp is None:
                self.logger.warning(f"[{self.device_id}] 입구 온도 읽기 실패")
                # 실패해도 계속 진행 (부분 데이터라도 수집)
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. 온도센서 2 읽기 (출구 온도)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            output_temp = self.read_temperature_2()
            if output_temp is None:
                self.logger.warning(f"[{self.device_id}] 출구 온도 읽기 실패")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 3. 유량센서 읽기
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            flow = self.read_flow()
            if flow is None:
                self.logger.warning(f"[{self.device_id}] 유량 읽기 실패")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 4. 결과 반환
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 모든 센서가 실패하면 None 반환
            if input_temp is None and output_temp is None and flow is None:
                self.logger.error(f"[{self.device_id}] 모든 센서 읽기 실패")
                return None
            
            # 부분 성공이라도 데이터 반환
            result = {
                'input_temp': input_temp,
                'output_temp': output_temp,
                'flow': flow
            }
            
            self.logger.info(
                f"[{self.device_id}] 센서 데이터 읽기 완료: "
                f"입구={input_temp}°C, 출구={output_temp}°C, 유량={flow}L/min"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                f"[{self.device_id}] 센서 읽기 오류: {e}",
                exc_info=True
            )
            return None
    
    def is_connected(self) -> bool:
        """
        연결 상태 확인
        
        Modbus TCP 매니저에 해당 IP:Port로 연결이 있는지 확인합니다.
        
        Returns:
            bool: 연결되어 있으면 True
            
        Example:
            >>> if reader.is_connected():
            >>>     print("연결됨")
            >>> else:
            >>>     print("연결 안 됨")
        """
        return self.modbus_manager.is_connected(self.ip, self.port)
    
    def update_slave_ids(
        self,
        temp1_slave_id: Optional[int] = None,
        temp2_slave_id: Optional[int] = None,
        flow_slave_id: Optional[int] = None
    ):
        """
        Slave ID 업데이트 (런타임 중 변경 가능)
        
        현장에서 Slave ID가 바뀌었을 때 프로그램을 재시작하지 않고
        동적으로 변경할 수 있습니다.
        
        Args:
            temp1_slave_id: 온도센서 1 Slave ID (None이면 유지)
            temp2_slave_id: 온도센서 2 Slave ID (None이면 유지)
            flow_slave_id: 유량센서 Slave ID (None이면 유지)
            
        Example:
            >>> # 유량 센서의 Slave ID만 변경
            >>> reader.update_slave_ids(flow_slave_id=12)
            
            >>> # 모든 Slave ID 변경
            >>> reader.update_slave_ids(
            >>>     temp1_slave_id=10,
            >>>     temp2_slave_id=11,
            >>>     flow_slave_id=12
            >>> )
        """
        if temp1_slave_id is not None:
            self.temp1_slave_id = temp1_slave_id
            self.logger.info(f"[{self.device_id}] 온도1 Slave ID 변경: {temp1_slave_id}")
        
        if temp2_slave_id is not None:
            self.temp2_slave_id = temp2_slave_id
            self.logger.info(f"[{self.device_id}] 온도2 Slave ID 변경: {temp2_slave_id}")
        
        if flow_slave_id is not None:
            self.flow_slave_id = flow_slave_id
            self.logger.info(f"[{self.device_id}] 유량 Slave ID 변경: {flow_slave_id}")


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """
    BoxSensorReader 테스트
    
    실행: python src/sensors/box/reader.py
    
    주의: 실제 센서 장비가 연결되어 있어야 합니다!
    """
    import sys
    from pathlib import Path

    # 프로젝트 루트를 sys.path에 추가
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    sys.path.insert(0, str(project_root))

    from core.logging_config import setup_logging
    from sensors.box.reader import BoxSensorReader

    # 로깅 설정
    setup_logging(log_level="DEBUG")

    print("=" * 70)
    print("BoxSensorReader 테스트 (실제 장비)")
    print("=" * 70)

    # 테스트할 장치 정보 (실제 통신 데이터 기반)
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
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 연결 확인
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 1] 연결 확인")
    if reader.is_connected():
        print("✓ 연결됨")
    else:
        print("ℹ️  연결 시도 중...")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 개별 센서 읽기
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 전체 센서 읽기
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 3] 전체 센서 읽기")
    data = reader.read_all_sensors()
    
    if data:
        print("  ✓ 읽기 성공:")
        print(f"    입구 온도: {data['input_temp']}°C")
        print(f"    출구 온도: {data['output_temp']}°C")
        print(f"    유량: {data['flow']} L/min")
        
        # 온도 차이 계산
        if data['input_temp'] is not None and data['output_temp'] is not None:
            temp_diff = data['output_temp'] - data['input_temp']
            print(f"    온도 차이: {temp_diff}°C")
    else:
        print("  ✗ 읽기 실패")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. 반복 읽기 테스트 (3회)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 4] 반복 읽기 (3회)")
    
    for i in range(3):
        print(f"\n  #{i+1}회:")
        data = reader.read_all_sensors()
        
        if data:
            print(f"    입구={data['input_temp']}°C, "
                  f"출구={data['output_temp']}°C, "
                  f"유량={data['flow']}L/min")
        else:
            print(f"    실패")
        
        # 다음 읽기까지 대기
        if i < 2:
            import time
            time.sleep(1)
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
