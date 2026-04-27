# ==============================================
# 온도, 유량 센서 데이터 수집기 (병렬 수집 버전)
# ==============================================
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, Optional
from datetime import datetime

from services.config_service import ConfigService
from sensors.box.reader import BoxSensorReader
from core.database import insert_heatpump_batch, insert_groundpipe_batch

logger = logging.getLogger(__name__)

# 장치별 수집 타임아웃 (초)
# 연결 타임아웃 2초 × 3회 재시도 × 3개 센서 + 여유 5초 = 23초
DEVICE_COLLECT_TIMEOUT = 25
# 병렬 수집 워커 수
MAX_WORKERS = 8


class BoxSensorCollector:
    """
    온도, 유량 센서 수집기

    개선 사항:
    - ThreadPoolExecutor로 장치별 병렬 수집
    - 한 장치의 타임아웃/오류가 다른 장치에 영향 없음
    - Circuit Breaker와 연동하여 불량 장치 자동 스킵
    """

    def __init__(self):
        self.config_service = ConfigService()
        self.readers: Dict[str, BoxSensorReader] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix="SensorWorker"
        )
        logger.info("BoxSensorCollector 초기화 완료 "
                    f"(병렬 워커: {MAX_WORKERS}개)")

    def _get_or_create_reader(self, device_id, ip, port,
                               temp1_slave_id, temp2_slave_id,
                               flow_slave_id) -> BoxSensorReader:
        cache_key = f"{ip}:{port}:{device_id}"
        if cache_key not in self.readers:
            self.readers[cache_key] = BoxSensorReader(
                device_id=device_id, ip=ip, port=port,
                temp1_slave_id=temp1_slave_id,
                temp2_slave_id=temp2_slave_id,
                flow_slave_id=flow_slave_id
            )
        else:
            reader = self.readers[cache_key]
            if (reader.temp1_slave_id != temp1_slave_id or
                    reader.temp2_slave_id != temp2_slave_id or
                    reader.flow_slave_id != flow_slave_id):
                reader.update_slave_ids(
                    temp1_slave_id, temp2_slave_id, flow_slave_id
                )
        return self.readers[cache_key]

    # ─────────────────────────────────────────
    # 단일 장치 수집 (워커 스레드에서 실행)
    # ─────────────────────────────────────────
    def _read_heatpump_sensor(self, device_id: str,
                                power_meter_data=None) -> dict:
        """센서 읽기만 수행 (DB 저장 없음)"""
        try:
            device_config = self.config_service.get_device_config(device_id)
            if not device_config or not device_config.get('enabled', True):
                return None

            ip      = device_config.get('ip')
            port    = device_config.get('port', 502)
            sensors = device_config.get('sensors', {})
            reader  = self._get_or_create_reader(
                device_id, ip, port,
                sensors.get('temp1_slave_id', 1),
                sensors.get('temp2_slave_id', 2),
                sensors.get('flow_slave_id', 3)
            )
            return reader.read_all_sensors()  # {'input_temp', 'output_temp', 'flow'}

        except Exception as e:
            logger.error(f"[{device_id}] 센서 읽기 오류: {e}", exc_info=True)
            return None

    # ─────────────────────────────────────────
    # 전체 병렬 수집
    # ─────────────────────────────────────────
    def collect_all_heatpumps(self, power_meter_data=None):
        heatpumps = self.config_service.get_heatpump_ips()
        logger.info(f"히트펌프 {len(heatpumps)}개 병렬 수집 시작")

        # 병렬로 센서 읽기만 수행
        futures = {}
        for hp in heatpumps:
            device_id = hp.get('device_id')
            if device_id:
                future = self._executor.submit(
                    self._read_heatpump_sensor, device_id, power_meter_data
                )
                futures[future] = device_id

        # 결과 수집
        # collect_all_groundpipes() 수정
        sensor_results = {}
        total_timeout = DEVICE_COLLECT_TIMEOUT * len(futures) / MAX_WORKERS + 5

        try:
            for future in as_completed(futures, timeout=total_timeout):
                device_id = futures[future]
                try:
                    sensor_results[device_id] = future.result(timeout=DEVICE_COLLECT_TIMEOUT)
                except Exception as e:
                    logger.error(f"[{device_id}] future 오류: {e}")
                    sensor_results[device_id] = None
        except TimeoutError:
            # 타임아웃 발생 시 완료된 것만 사용, 나머지는 실패 처리
            logger.warning(f"히트펌프 수집 타임아웃 — 완료된 {len(sensor_results)}개만 저장")
            for future, device_id in futures.items():
                if device_id not in sensor_results:
                    sensor_results[device_id] = None

        # 배치 INSERT (한 트랜잭션)
        batch = []
        results = {}
        now = datetime.now()

        for device_id, data in sensor_results.items():
            if data:
                energy = power_meter_data.get(device_id) if power_meter_data else None
                batch.append({
                    'device_id':   device_id,
                    'input_temp':  data.get('input_temp'),
                    'output_temp': data.get('output_temp'),
                    'flow':        data.get('flow'),
                    'energy':      energy,
                    'timestamp':   now,
                })
                results[device_id] = {'success': True, 'flow': data.get('flow')}
                logger.info(
                    f"[{device_id}] 수집 완료 "
                    f"T_in={data.get('input_temp')}°C "
                    f"T_out={data.get('output_temp')}°C "
                    f"Flow={data.get('flow')}L"
                )
            else:
                results[device_id] = {'success': False, 'flow': None}

        if batch:
            insert_heatpump_batch(batch)

        # 타임아웃으로 결과 없는 장치
        for hp in heatpumps:
            device_id = hp.get('device_id')
            if device_id and device_id not in results:
                results[device_id] = {'success': False, 'flow': None}

        success_count = sum(1 for v in results.values() if v.get('success'))
        logger.info(f"히트펌프 수집 완료: {success_count}/{len(heatpumps)}개 성공")
        return results

    def collect_all_groundpipes(self):
        groundpipes = self.config_service.get_groundpipe_ips()
        logger.info(f"지중배관 {len(groundpipes)}개 병렬 수집 시작")

        futures = {}
        for gp in groundpipes:
            device_id = gp.get('device_id')
            if device_id:
                future = self._executor.submit(
                    self._read_groundpipe_sensor, device_id
                )
                futures[future] = device_id

        sensor_results = {}
        total_timeout = DEVICE_COLLECT_TIMEOUT * len(futures) / MAX_WORKERS + 5

        try:
            for future in as_completed(futures, timeout=total_timeout):
                device_id = futures[future]
                try:
                    sensor_results[device_id] = future.result(timeout=DEVICE_COLLECT_TIMEOUT)
                except Exception as e:
                    logger.error(f"[{device_id}] future 오류: {e}")
                    sensor_results[device_id] = None
        except TimeoutError:
            # 타임아웃 발생 시 완료된 것만 사용, 나머지는 실패 처리
            logger.warning(f"지중배관 수집 타임아웃 — 완료된 {len(sensor_results)}개만 저장")
            for future, device_id in futures.items():
                if device_id not in sensor_results:
                    sensor_results[device_id] = None

        batch = []
        results = {}
        now = datetime.now()

        for device_id, data in sensor_results.items():
            if data:
                batch.append({
                    'device_id':   device_id,
                    'input_temp':  data.get('input_temp'),
                    'output_temp': data.get('output_temp'),
                    'flow':        data.get('flow'),
                    'timestamp':   now,
                })
                results[device_id] = {'success': True, 'flow': data.get('flow')}
                logger.info(f"[{device_id}] 수집 완료")
            else:
                results[device_id] = {'success': False, 'flow': None}

        if batch:
            insert_groundpipe_batch(batch)

        for gp in groundpipes:
            device_id = gp.get('device_id')
            if device_id and device_id not in results:
                results[device_id] = {'success': False, 'flow': None}

        success_count = sum(1 for v in results.values() if v.get('success'))
        logger.info(f"지중배관 수집 완료: {success_count}/{len(groundpipes)}개 성공")
        return results

    def _read_groundpipe_sensor(self, device_id: str) -> dict:
        """센서 읽기만 수행 (DB 저장 없음)"""
        try:
            device_config = self.config_service.get_device_config(device_id)
            if not device_config or not device_config.get('enabled', True):
                return None

            ip      = device_config.get('ip')
            port    = device_config.get('port', 502)
            sensors = device_config.get('sensors', {})
            reader  = self._get_or_create_reader(
                device_id, ip, port,
                sensors.get('temp1_slave_id', 1),
                sensors.get('temp2_slave_id', 2),
                sensors.get('flow_slave_id', 3)
            )
            return reader.read_all_sensors()

        except Exception as e:
            logger.error(f"[{device_id}] 센서 읽기 오류: {e}", exc_info=True)
            return None

    def collect_all(self, power_meter_data=None) -> dict:
        """
        전체 장치 병렬 수집.
        히트펌프와 지중배관을 동시에 수집.
        """
        logger.info("온도, 유량 전체 병렬 수집 시작")

        # 히트펌프 + 지중배관 동시 수집
        hp_future = self._executor.submit(
            self.collect_all_heatpumps, power_meter_data
        )
        gp_future = self._executor.submit(
            self.collect_all_groundpipes
        )

        # 내부에서 total_timeout = 25 × 10 / 8 + 5 = 36.25초
        # 외부가 50초라 충분하긴 한데, 더 명확하게 장치 수 기반으로
        hp_count = len(self.config_service.get_heatpump_ips())
        gp_count = len(self.config_service.get_groundpipe_ips())

        try:
            hp_results = hp_future.result(
                timeout=DEVICE_COLLECT_TIMEOUT * hp_count / MAX_WORKERS + 10 
            )
        except Exception as e:
            logger.error(f"히트펌프 전체 수집 오류: {e}")
            hp_results = {}

        try:
            gp_results = gp_future.result(
                timeout=DEVICE_COLLECT_TIMEOUT * gp_count / MAX_WORKERS + 10
            )
        except Exception as e:
            logger.error(f"지중배관 전체 수집 오류: {e}")
            gp_results = {}

        results = {'heatpump': hp_results, 'groundpipe': gp_results}

        total_success = (
            sum(1 for v in hp_results.values() if v.get('success')) +
            sum(1 for v in gp_results.values() if v.get('success'))
        )
        total_count = len(hp_results) + len(gp_results)
        logger.info(
            f"전체 수집 완료: {total_success}/{total_count}개 성공"
        )
        return results

    def __del__(self):
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass