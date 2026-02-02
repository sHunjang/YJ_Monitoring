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
- 0x0404 (1028): 누적 전력량 시작 레지스터
- 데이터 타입: 32bit Long (2개 레지스터)
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
    
    # 레지스터 주소 (수정됨)
    REGISTER_ENERGY = 0x0404  # 누적 전력량 시작 레지스터 (1028번)
    
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
        logger.info(f"  레지스터 주소: 0x{self.REGISTER_ENERGY:04X}")
    
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
            
            # 레지스터 읽기 (2개 워드 = 32bit Long)
            result = client.read_holding_registers(
                address=self.REGISTER_ENERGY,
                count=2,
                slave=slave_id
            )
            
            if result.isError():
                logger.error(f"[Slave {slave_id}] Modbus 읽기 오류: {result}")
                return None
            
            # 상위/하위 워드
            high_word = result.registers[0]
            low_word = result.registers[1]
            
            # 디버깅 로그 (DEBUG 레벨)
            logger.debug(
                f"[Slave {slave_id}] RAW 데이터: "
                f"High=0x{high_word:04X} ({high_word}), "
                f"Low=0x{low_word:04X} ({low_word})"
            )
            
            # 32비트 값 계산 (Big Endian)
            raw_value = (high_word << 16) | low_word
            
            logger.debug(
                f"[Slave {slave_id}] 32bit Long: {raw_value} "
                f"(0x{raw_value:08X})"
            )
            
            # kWh 변환 (0.01 kWh 단위)
            energy_kwh = raw_value * 0.01
            
            logger.debug(
                f"[Slave {slave_id}] 전력량: {energy_kwh:.2f} kWh"
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
                    
                    logger.info(
                        f"✓ [{meter_config.device_id}] {total_energy:.2f} kWh"
                    )
                else:
                    fail_count += 1
                    logger.warning(f"✗ [{meter_config.device_id}] 데이터 읽기 실패")
                    
            except Exception as e:
                fail_count += 1
                logger.error(
                    f"✗ [{meter_config.device_id}] 데이터 읽기 오류: {e}",
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
    import sys
    from pathlib import Path
    
    # 프로젝트 루트를 sys.path에 추가
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    sys.path.insert(0, str(project_root / 'src'))
    
    from core.logging_config import setup_logging
    
    setup_logging(log_level="DEBUG")
    
    print("=" * 70)
    print("전력량계 Reader 테스트")
    print("=" * 70)
    
    try:
        reader = PowerMeterReader()
        
        print(f"\n[설정 정보]")
        print(f"  IP: {reader.ip}:{reader.port}")
        print(f"  레지스터: 0x{reader.REGISTER_ENERGY:04X} ({reader.REGISTER_ENERGY})")
        print(f"  전력량계: {len(reader.meter_configs)}개")
        
        print(f"\n[데이터 읽기]")
        data = reader.read_all_meters()
        
        print(f"\n[결과]")
        if data:
            for device_id, meter_data in data.items():
                print(f"  ✓ {device_id}: {meter_data.total_energy:.2f} kWh")
        else:
            print("  ✗ 데이터 없음")
        
        reader.close()
        
        print("\n" + "=" * 70)
        print("✓ 테스트 완료")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
