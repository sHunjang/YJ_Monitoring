# ==============================================
# 플라스틱 함 센서 서비스
# ==============================================
import logging
import threading
import time
from typing import Optional, Dict, Callable
from datetime import datetime

from sensors.box.collector import BoxSensorCollector
from core.config import get_config

logger = logging.getLogger(__name__)


class BoxSensorService:
    def __init__(self):
        self.config = get_config()
        self.collector = BoxSensorCollector()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self.stats = {'total_collections': 0, 'successful_collections': 0,
                      'failed_collections': 0, 'last_collection_time': None,
                      'last_success_time': None, 'last_error': None}
        self.on_collection_complete: Optional[Callable] = None
        self.on_collection_error: Optional[Callable] = None
        logger.info("BoxSensorService 초기화 완료")

    def start(self, interval: Optional[int] = None):
        if self._running:
            logger.warning("이미 실행 중입니다."); return
        self.interval = interval or self.config.collection_interval
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._collection_loop, daemon=True, name="BoxSensorService")
        self._thread.start()
        logger.info(f"BoxSensorService 시작 (주기: {self.interval}초)")

    def stop(self):
        if not self._running:
            logger.warning("실행 중이 아닙니다."); return
        logger.info("BoxSensorService 중지 요청")
        self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("BoxSensorService 중지 완료")

    def _collection_loop(self):
        logger.info("데이터 수집 루프 시작")
        while not self._stop_event.is_set():
            try:
                self._collect_once()
            except Exception as e:
                logger.error(f"데이터 수집 루프 오류: {e}", exc_info=True)
                self.stats['last_error'] = str(e)
                if self.on_collection_error:
                    try: self.on_collection_error(str(e))
                    except: pass
            self._stop_event.wait(self.interval)
        logger.info("데이터 수집 루프 종료")

    def _collect_once(self, power_meter_data: Optional[Dict[str, float]] = None):
        start_time = time.time()
        self.stats['total_collections'] += 1
        self.stats['last_collection_time'] = datetime.now()
        try:
            results = self.collector.collect_all(power_meter_data)
            total_success = (sum(1 for v in results['heatpump'].values() if v) +
                             sum(1 for v in results['groundpipe'].values() if v))
            total_count = len(results['heatpump']) + len(results['groundpipe'])
            if total_success > 0:
                self.stats['successful_collections'] += 1
                self.stats['last_success_time'] = datetime.now()
            else:
                self.stats['failed_collections'] += 1
            elapsed_time = time.time() - start_time
            logger.info(f"플라스틱 함 센서 데이터 수집 완료: {total_success}/{total_count}개 성공, 소요 시간: {elapsed_time:.2f}초")
            if self.on_collection_complete:
                try: self.on_collection_complete(results)
                except: pass
        except Exception as e:
            self.stats['failed_collections'] += 1
            self.stats['last_error'] = str(e)
            logger.error(f"플라스틱 함 센서 데이터 수집 실패: {e}", exc_info=True)
            if self.on_collection_error:
                try: self.on_collection_error(str(e))
                except: pass

    def collect_now(self, power_meter_data=None):
        logger.info("수동 데이터 수집 트리거")
        self._collect_once(power_meter_data)

    def is_running(self): return self._running
    def get_stats(self): return self.stats.copy()

    def reset_stats(self):
        self.stats = {'total_collections': 0, 'successful_collections': 0,
                      'failed_collections': 0, 'last_collection_time': None,
                      'last_success_time': None, 'last_error': None}
        logger.info("통계 초기화")
