# ==============================================
# 플라스틱 함 센서 데이터 수집기
# ==============================================
import logging
from typing import Dict, List, Optional
from datetime import datetime

from services.config_service import ConfigService
from sensors.box.reader import BoxSensorReader
from core.database import insert_heatpump_data, insert_groundpipe_data

logger = logging.getLogger(__name__)


class BoxSensorCollector:
    def __init__(self):
        self.config_service = ConfigService()
        self.readers: Dict[str, BoxSensorReader] = {}
        logger.info("BoxSensorCollector 초기화 완료")

    def _get_or_create_reader(self, device_id, ip, port, temp1_slave_id, temp2_slave_id, flow_slave_id):
        cache_key = f"{ip}:{port}"
        if cache_key in self.readers:
            reader = self.readers[cache_key]
            if (reader.temp1_slave_id != temp1_slave_id or
                reader.temp2_slave_id != temp2_slave_id or
                reader.flow_slave_id != flow_slave_id):
                reader.update_slave_ids(temp1_slave_id=temp1_slave_id,
                                        temp2_slave_id=temp2_slave_id,
                                        flow_slave_id=flow_slave_id)
            return reader
        reader = BoxSensorReader(device_id=device_id, ip=ip, port=port,
                                  temp1_slave_id=temp1_slave_id,
                                  temp2_slave_id=temp2_slave_id,
                                  flow_slave_id=flow_slave_id)
        self.readers[cache_key] = reader
        return reader

    def collect_heatpump(self, device_id: str, power_meter_data: Optional[Dict[str, float]] = None) -> bool:
        try:
            device_config = self.config_service.get_device_config(device_id)
            if not device_config:
                logger.error(f"[{device_id}] 설정을 찾을 수 없음"); return False
            if not device_config.get('enabled', True):
                logger.debug(f"[{device_id}] 비활성화됨"); return False

            ip = device_config.get('ip')
            port = device_config.get('port', 502)
            sensors = device_config.get('sensors', {})
            reader = self._get_or_create_reader(device_id, ip, port,
                sensors.get('temp1_slave_id', 1), sensors.get('temp2_slave_id', 2), sensors.get('flow_slave_id', 3))

            sensor_data = reader.read_all_sensors()
            if not sensor_data:
                logger.error(f"[{device_id}] 센서 데이터 읽기 실패")
                return {'success': False, 'flow': None}

            energy = power_meter_data.get(device_id) if power_meter_data else None
            success = insert_heatpump_data(device_id=device_id,
                input_temp=sensor_data.get('input_temp'), output_temp=sensor_data.get('output_temp'),
                flow=sensor_data.get('flow'), energy=energy, timestamp=datetime.now())
            if success:
                return {'success': True, 'flow': sensor_data.get('flow')}
            else:
                return {'success': False, 'flow': None}
        except Exception as e:
            logger.error(f"[{device_id}] 데이터 수집 오류: {e}", exc_info=True)
            return {'success': False, 'flow': None}


    def collect_groundpipe(self, device_id: str) -> bool:
        try:
            device_config = self.config_service.get_device_config(device_id)
            if not device_config:
                logger.error(f"[{device_id}] 설정을 찾을 수 없음"); return False
            if not device_config.get('enabled', True):
                logger.debug(f"[{device_id}] 비활성화됨"); return False

            ip = device_config.get('ip')
            port = device_config.get('port', 502)
            sensors = device_config.get('sensors', {})
            reader = self._get_or_create_reader(device_id, ip, port,
                sensors.get('temp1_slave_id', 1), sensors.get('temp2_slave_id', 2), sensors.get('flow_slave_id', 3))

            sensor_data = reader.read_all_sensors()
            if not sensor_data:
                logger.error(f"[{device_id}] 센서 데이터 읽기 실패")
                return {'success': False, 'flow': None}

            success = insert_groundpipe_data(device_id=device_id,
                input_temp=sensor_data.get('input_temp'), output_temp=sensor_data.get('output_temp'),
                flow=sensor_data.get('flow'), timestamp=datetime.now())
            if success:
                return {'success': True, 'flow': sensor_data.get('flow')}
            else:
                return {'success': False, 'flow': None}
                        
        except Exception as e:
            logger.error(f"[{device_id}] 데이터 수집 오류: {e}", exc_info=True)
            return {'success': False, 'flow': None}

    def collect_all_heatpumps(self, power_meter_data=None):
        results = {}
        heatpumps = self.config_service.get_heatpump_ips()
        logger.info(f"히트펌프 {len(heatpumps)}개 데이터 수집 시작")
        for hp in heatpumps:
            device_id = hp.get('device_id')
            if device_id:
                result = self.collect_heatpump(device_id, power_meter_data)
                results[device_id] = result
        logger.info(f"히트펌프 데이터 수집 완료: {sum(1 for v in results.values() if v.get('success'))}/{len(heatpumps)}개 성공")
        return results

    def collect_all_groundpipes(self):
        results = {}
        groundpipes = self.config_service.get_groundpipe_ips()
        logger.info(f"지중배관 {len(groundpipes)}개 데이터 수집 시작")
        for gp in groundpipes:
            device_id = gp.get('device_id')
            if device_id:
                results[device_id] = self.collect_groundpipe(device_id)
        logger.info(f"지중배관 데이터 수집 완료: {sum(1 for v in results.values() if v.get('success'))}/{len(groundpipes)}개 성공")
        return results

    def collect_all(self, power_meter_data=None):
        logger.info("플라스틱 함 센서 전체 데이터 수집 시작")
        results = {
            'heatpump': self.collect_all_heatpumps(power_meter_data),
            'groundpipe': self.collect_all_groundpipes()
        }
        total_success = sum(1 for v in results['heatpump'].values() if v.get('success')) + sum(1 for v in results['groundpipe'].values() if v.get('success'))
        total_count = len(results['heatpump']) + len(results['groundpipe'])
        logger.info(f"플라스틱 함 센서 전체 데이터 수집 완료: {total_success}/{total_count}개 성공")
        return results
