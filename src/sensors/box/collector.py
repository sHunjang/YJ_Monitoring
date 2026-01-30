# ==============================================
# 플라스틱 함 센서 데이터 수집기
# ==============================================
"""
플라스틱 함 센서 주기적 데이터 수집

주요 기능:
1. 설정 파일에서 장치 목록 로드
2. 각 장치의 센서 데이터 읽기
3. 데이터베이스에 저장
4. 전력량계 데이터와 결합 (히트펌프만)

사용 예:
    from sensors.box.collector import BoxSensorCollector
    
    collector = BoxSensorCollector()
    collector.collect_all()
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from services.config_service import ConfigService
from sensors.box.reader import BoxSensorReader
from core.database import insert_heatpump_data, insert_groundpipe_data

logger = logging.getLogger(__name__)


class BoxSensorCollector:
    """
    플라스틱 함 센서 데이터 수집기
    
    히트펌프와 지중배관의 센서 데이터를 주기적으로 수집하고 저장합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.config_service = ConfigService()
        
        # Reader 캐시 (IP별로 재사용)
        self.readers: Dict[str, BoxSensorReader] = {}
        
        logger.info("BoxSensorCollector 초기화 완료")
    
    def _get_or_create_reader(
        self,
        device_id: str,
        ip: str,
        port: int,
        temp1_slave_id: int,
        temp2_slave_id: int,
        flow_slave_id: int
    ) -> BoxSensorReader:
        """
        Reader 가져오기 또는 생성 (캐싱)
        
        Args:
            device_id: 장치 ID
            ip: IP 주소
            port: 포트
            temp1_slave_id: 온도1 Slave ID
            temp2_slave_id: 온도2 Slave ID
            flow_slave_id: 유량 Slave ID
            
        Returns:
            BoxSensorReader: Reader 인스턴스
        """
        # 캐시 키: IP:port
        cache_key = f"{ip}:{port}"
        
        if cache_key in self.readers:
            reader = self.readers[cache_key]
            
            # Slave ID가 변경되었으면 업데이트
            if (reader.temp1_slave_id != temp1_slave_id or
                reader.temp2_slave_id != temp2_slave_id or
                reader.flow_slave_id != flow_slave_id):
                
                reader.update_slave_ids(
                    temp1_slave_id=temp1_slave_id,
                    temp2_slave_id=temp2_slave_id,
                    flow_slave_id=flow_slave_id
                )
            
            return reader
        else:
            # 새 Reader 생성
            reader = BoxSensorReader(
                device_id=device_id,
                ip=ip,
                port=port,
                temp1_slave_id=temp1_slave_id,
                temp2_slave_id=temp2_slave_id,
                flow_slave_id=flow_slave_id
            )
            
            self.readers[cache_key] = reader
            return reader
    
    def collect_heatpump(
        self,
        device_id: str,
        power_meter_data: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        히트펌프 데이터 수집 및 저장
        
        Args:
            device_id: 히트펌프 ID (예: 'HP_1')
            power_meter_data: 전력량계 데이터 {device_id: energy}
            
        Returns:
            bool: 수집 성공 시 True
        """
        try:
            # 설정 파일에서 장치 정보 로드
            device_config = self.config_service.get_device_config(device_id)
            
            if not device_config:
                logger.error(f"[{device_id}] 설정을 찾을 수 없음")
                return False
            
            if not device_config.get('enabled', True):
                logger.debug(f"[{device_id}] 비활성화됨 (enabled=false)")
                return False
            
            # IP 및 Slave ID 추출
            ip = device_config.get('ip')
            port = device_config.get('port', 502)
            sensors = device_config.get('sensors', {})
            
            temp1_slave_id = sensors.get('temp1_slave_id', 1)
            temp2_slave_id = sensors.get('temp2_slave_id', 2)
            flow_slave_id = sensors.get('flow_slave_id', 3)
            
            # Reader 가져오기
            reader = self._get_or_create_reader(
                device_id=device_id,
                ip=ip,
                port=port,
                temp1_slave_id=temp1_slave_id,
                temp2_slave_id=temp2_slave_id,
                flow_slave_id=flow_slave_id
            )
            
            # 센서 데이터 읽기
            sensor_data = reader.read_all_sensors()
            
            if not sensor_data:
                logger.error(f"[{device_id}] 센서 데이터 읽기 실패")
                return False
            
            # 전력량 데이터 추가
            energy = None
            if power_meter_data and device_id in power_meter_data:
                energy = power_meter_data[device_id]
            
            # 데이터베이스에 저장
            timestamp = datetime.now()
            
            success = insert_heatpump_data(
                device_id=device_id,
                input_temp=sensor_data.get('input_temp'),
                output_temp=sensor_data.get('output_temp'),
                flow=sensor_data.get('flow'),
                energy=energy,
                timestamp=timestamp
            )
            
            if success:
                logger.info(
                    f"[{device_id}] 데이터 저장 완료: "
                    f"T_in={sensor_data.get('input_temp')}°C, "
                    f"T_out={sensor_data.get('output_temp')}°C, "
                    f"Flow={sensor_data.get('flow')}L/min, "
                    f"Energy={energy}kWh"
                )
            else:
                logger.error(f"[{device_id}] 데이터 저장 실패")
            
            return success
            
        except Exception as e:
            logger.error(f"[{device_id}] 데이터 수집 오류: {e}", exc_info=True)
            return False
    
    def collect_groundpipe(self, device_id: str) -> bool:
        """
        지중배관 데이터 수집 및 저장
        
        Args:
            device_id: 지중배관 ID (예: 'GP_1')
            
        Returns:
            bool: 수집 성공 시 True
        """
        try:
            # 설정 파일에서 장치 정보 로드
            device_config = self.config_service.get_device_config(device_id)
            
            if not device_config:
                logger.error(f"[{device_id}] 설정을 찾을 수 없음")
                return False
            
            if not device_config.get('enabled', True):
                logger.debug(f"[{device_id}] 비활성화됨 (enabled=false)")
                return False
            
            # IP 및 Slave ID 추출
            ip = device_config.get('ip')
            port = device_config.get('port', 502)
            sensors = device_config.get('sensors', {})
            
            temp1_slave_id = sensors.get('temp1_slave_id', 1)
            temp2_slave_id = sensors.get('temp2_slave_id', 2)
            flow_slave_id = sensors.get('flow_slave_id', 3)
            
            # Reader 가져오기
            reader = self._get_or_create_reader(
                device_id=device_id,
                ip=ip,
                port=port,
                temp1_slave_id=temp1_slave_id,
                temp2_slave_id=temp2_slave_id,
                flow_slave_id=flow_slave_id
            )
            
            # 센서 데이터 읽기
            sensor_data = reader.read_all_sensors()
            
            if not sensor_data:
                logger.error(f"[{device_id}] 센서 데이터 읽기 실패")
                return False
            
            # 데이터베이스에 저장
            timestamp = datetime.now()
            
            success = insert_groundpipe_data(
                device_id=device_id,
                input_temp=sensor_data.get('input_temp'),
                output_temp=sensor_data.get('output_temp'),
                flow=sensor_data.get('flow'),
                timestamp=timestamp
            )
            
            if success:
                logger.info(
                    f"[{device_id}] 데이터 저장 완료: "
                    f"T_in={sensor_data.get('input_temp')}°C, "
                    f"T_out={sensor_data.get('output_temp')}°C, "
                    f"Flow={sensor_data.get('flow')}L/min"
                )
            else:
                logger.error(f"[{device_id}] 데이터 저장 실패")
            
            return success
            
        except Exception as e:
            logger.error(f"[{device_id}] 데이터 수집 오류: {e}", exc_info=True)
            return False
    
    def collect_all_heatpumps(
        self,
        power_meter_data: Optional[Dict[str, float]] = None
    ) -> Dict[str, bool]:
        """
        모든 히트펌프 데이터 수집
        
        Args:
            power_meter_data: 전력량계 데이터
            
        Returns:
            dict: {device_id: success}
        """
        results = {}
        
        heatpumps = self.config_service.get_heatpump_ips()
        
        logger.info(f"히트펌프 {len(heatpumps)}개 데이터 수집 시작")
        
        for hp in heatpumps:
            device_id = hp.get('device_id')
            if device_id:
                success = self.collect_heatpump(device_id, power_meter_data)
                results[device_id] = success
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"히트펌프 데이터 수집 완료: {success_count}/{len(heatpumps)}개 성공"
        )
        
        return results
    
    def collect_all_groundpipes(self) -> Dict[str, bool]:
        """
        모든 지중배관 데이터 수집
        
        Returns:
            dict: {device_id: success}
        """
        results = {}
        
        groundpipes = self.config_service.get_groundpipe_ips()
        
        logger.info(f"지중배관 {len(groundpipes)}개 데이터 수집 시작")
        
        for gp in groundpipes:
            device_id = gp.get('device_id')
            if device_id:
                success = self.collect_groundpipe(device_id)
                results[device_id] = success
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"지중배관 데이터 수집 완료: {success_count}/{len(groundpipes)}개 성공"
        )
        
        return results
    
    def collect_all(
        self,
        power_meter_data: Optional[Dict[str, float]] = None
    ) -> Dict[str, Dict[str, bool]]:
        """
        모든 플라스틱 함 센서 데이터 수집
        
        Args:
            power_meter_data: 전력량계 데이터
            
        Returns:
            dict: {
                'heatpump': {device_id: success},
                'groundpipe': {device_id: success}
            }
        """
        logger.info("=" * 70)
        logger.info("플라스틱 함 센서 전체 데이터 수집 시작")
        logger.info("=" * 70)
        
        results = {
            'heatpump': self.collect_all_heatpumps(power_meter_data),
            'groundpipe': self.collect_all_groundpipes()
        }
        
        total_success = (
            sum(1 for v in results['heatpump'].values() if v) +
            sum(1 for v in results['groundpipe'].values() if v)
        )
        total_count = len(results['heatpump']) + len(results['groundpipe'])
        
        logger.info("=" * 70)
        logger.info(f"플라스틱 함 센서 전체 데이터 수집 완료: {total_success}/{total_count}개 성공")
        logger.info("=" * 70)
        
        return results


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """BoxSensorCollector 테스트"""
    import sys
    from pathlib import Path
    
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent
    sys.path.insert(0, str(project_root / 'src'))
    
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="INFO")
    
    print("=" * 70)
    print("BoxSensorCollector 테스트")
    print("=" * 70)
    
    # 데이터베이스 초기화
    initialize_connection_pool()
    
    # Collector 생성
    collector = BoxSensorCollector()
    
    # 전체 수집 테스트
    print("\n[테스트] 전체 데이터 수집")
    
    # 전력량계 데이터 (예시)
    power_meter_data = {
        'HP_1': 123.45,
        'HP_2': 234.56,
        'HP_3': 345.67,
        'HP_4': 456.78
    }
    
    results = collector.collect_all(power_meter_data)
    
    print("\n히트펌프 결과:")
    for device_id, success in results['heatpump'].items():
        status = "✓" if success else "✗"
        print(f"  {status} {device_id}")
    
    print("\n지중배관 결과:")
    for device_id, success in results['groundpipe'].items():
        status = "✓" if success else "✗"
        print(f"  {status} {device_id}")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
