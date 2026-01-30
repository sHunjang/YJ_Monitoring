# ==============================================
# 전력량계 데이터 읽기 모듈
# ==============================================
"""
전력량계 Modbus RTU over TCP 통신

주요 기능:
1. 전력량계 설정 로드 (JSON)
2. Modbus RTU over TCP 통신
3. 전력량 데이터 읽기

레지스터 맵:
- 0x0048 (72): 누적 전력량 상위 워드
- 0x0049 (73): 누적 전력량 하위 워드
- 단위: 0.01 kWh (값 / 100)

사용 예:
    from sensors.power.reader import PowerMeterReader
    
    reader = PowerMeterReader()
    data = reader.read_all_meters()
    for device_id, meter_data in data.items():
        print(f"{device_id}: {meter_data.total_energy} kWh")
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from sensors.power.models import PowerMeterData, PowerMeterSystemConfig
from core.modbus_tcp_manager import ModbusTcpManager

logger = logging.getLogger(__name__)


class PowerMeterReader:
    """전력량계 데이터 읽기"""
    
    # 레지스터 주소
    REGISTER_ENERGY_HIGH = 0x0048  # 누적 전력량 상위 워드
    REGISTER_ENERGY_LOW = 0x0049   # 누적 전력량 하위 워드
    
    def __init__(self, config_file: str = 'config/power_meter_config.json'):
        """
        초기화
        
        Args:
            config_file: 설정 파일 경로
        """
        self.config_file = Path(config_file)
        
        # 설정 로드
        self.system_config = self._load_config()
        
        self.ip = self.system_config.ip
        self.port = self.system_config.port
        self.meter_configs = self.system_config.get_enabled_meters()
        
        # Modbus 매니저 초기화
        self.modbus_manager = ModbusTcpManager()
        
        logger.info(f"PowerMeterReader 초기화: {self.ip}:{self.port}")
        logger.info(f"  전력량계 개수: {len(self.meter_configs)}개")
    
    def _load_config(self) -> PowerMeterSystemConfig:
        """
        설정 파일 로드
        
        Returns:
            PowerMeterSystemConfig: 시스템 설정
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            system_config = PowerMeterSystemConfig.from_dict(config_data)
            
            logger.info(f"✓ 전력량계 설정 로드: {self.config_file}")
            logger.info(f"  IP: {system_config.ip}:{system_config.port}")
            logger.info(f"  전력량계: {len(system_config.meters)}개")
            
            return system_config
        
        except FileNotFoundError:
            logger.error(f"✗ 설정 파일을 찾을 수 없습니다: {self.config_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"✗ 설정 파일 JSON 파싱 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ 설정 파일 로드 오류: {e}")
            raise
    
    def read_total_energy(self, slave_id: int) -> Optional[float]:
        """
        누적 전력량 읽기
        
        Args:
            slave_id: Slave ID
        
        Returns:
            float: 누적 전력량 (kWh)
            None: 읽기 실패
        """
        try:
            # Modbus RTU over TCP 연결
            client = self.modbus_manager.get_client(self.ip, self.port)
            
            # 레지스터 읽기 (2개 워드)
            result = client.read_holding_registers(
                address=self.REGISTER_ENERGY_HIGH,
                count=2,
                slave=slave_id
            )
            
            if result.isError():
                logger.error(f"[Slave {slave_id}] Modbus 읽기 오류: {result}")
                return None
            
            # 상위/하위 워드 결합
            high_word = result.registers[0]
            low_word = result.registers[1]
            
            # 32비트 값 계산
            raw_value = (high_word << 16) | low_word
            
            # kWh 변환 (0.01 kWh 단위)
            energy_kwh = raw_value * 0.01
            
            logger.debug(
                f"[Slave {slave_id}] 전력량: {energy_kwh:.2f} kWh "
                f"(High: {high_word}, Low: {low_word})"
            )
            
            return energy_kwh
        
        except Exception as e:
            logger.error(f"[Slave {slave_id}] 전력량 읽기 오류: {e}", exc_info=True)
            return None
    
    def read_all_meters(self) -> Dict[str, PowerMeterData]:
        """
        모든 전력량계 데이터 읽기
        
        Returns:
            dict: {device_id: PowerMeterData, ...}
        """
        logger.info(f"전력량계 데이터 읽기 시작 ({self.ip}:{self.port})")
        
        results = {}
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for meter_config in self.meter_configs:
            # 비활성화된 전력량계는 건너뛰기
            if not meter_config.enabled:
                skip_count += 1
                continue
            
            try:
                # 전력량 읽기
                total_energy = self.read_total_energy(meter_config.slave_id)
                
                if total_energy is not None:
                    # PowerMeterData 객체 생성
                    data = PowerMeterData(
                        device_id=meter_config.device_id,
                        total_energy=total_energy
                    )
                    
                    results[meter_config.device_id] = data
                    success_count += 1
                    
                    logger.debug(
                        f"[{meter_config.device_id}] 전력량: {total_energy}kWh"
                    )
                else:
                    fail_count += 1
                    logger.warning(f"[{meter_config.device_id}] 데이터 읽기 실패")
            
            except Exception as e:
                fail_count += 1
                logger.error(
                    f"[{meter_config.device_id}] 데이터 읽기 오류: {e}",
                    exc_info=True
                )
        
        total_count = len(self.meter_configs)
        logger.info(
            f"전력량계 데이터 읽기 완료: "
            f"성공 {success_count}개, 실패 {fail_count}개, "
            f"건너뜀 {skip_count}개 (총 {total_count}개)"
        )
        
        return results
    
    def close(self):
        """연결 종료"""
        self.modbus_manager.close_all()
        logger.info("PowerMeterReader 연결 종료")


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    from core.logging_config import setup_logging
    
    setup_logging(log_level="DEBUG")
    
    print("=" * 70)
    print("전력량계 Reader 테스트")
    print("=" * 70)
    
    try:
        reader = PowerMeterReader()
        
        print(f"\n[설정 정보]")
        print(f"  IP: {reader.ip}:{reader.port}")
        print(f"  전력량계: {len(reader.meter_configs)}개")
        
        print(f"\n[데이터 읽기]")
        data = reader.read_all_meters()
        
        print(f"\n[결과]")
        for device_id, meter_data in data.items():
            print(f"  {device_id}: {meter_data.total_energy} kWh")
        
        reader.close()
        
        print("\n" + "=" * 70)
        print("✓ 테스트 완료")
        print("=" * 70)
    
    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
