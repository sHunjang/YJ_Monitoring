# ==============================================
# 통합 데이터 수집 서비스 (안정성 강화 버전)
# ==============================================
"""
플라스틱 함 센서 + 전력량계 통합 데이터 수집 서비스

안정성 강화:
1. Watchdog — 수집 루프가 멈추면 자동 재시작
2. 장치별 독립 수집 — 한 장치 실패가 다른 장치에 영향 없음
3. DB 연결 풀 자동 복구
4. 전역 예외 핸들러 등록
5. RemoteSyncService + AlarmService 통합
"""

import logging
import threading
import time
import sys
from typing import Optional, Dict, Callable
from datetime import datetime

from sensors.box.service import BoxSensorService
from sensors.power.service import PowerMeterService
from services.remote_sync_service import RemoteSyncService
from services.alarm_service import AlarmService
from core.config import get_config
from core.database import get_queue_count

logger = logging.getLogger(__name__)

# Watchdog 임계값 — 이 시간(초) 동안 수집이 없으면 루프 재시작
WATCHDOG_TIMEOUT = 300   # 5분
MAX_RESTART_COUNT = 10   # 최대 자동 재시작 횟수


class DataCollectionService:
    """통합 데이터 수집 서비스 (안정성 강화)"""

    def __init__(self):
        self.config = get_config()

        self.power_meter_service = PowerMeterService()
        self.box_sensor_service  = BoxSensorService()
        self.remote_sync_service = RemoteSyncService()
        self.alarm_service       = AlarmService.get_instance()

        self._thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop_event   = threading.Event()
        self._running      = False
        self.interval      = 60

        # Watchdog 상태
        self._last_collection_time: Optional[float] = None
        self._restart_count = 0

        # 통계
        self.stats = {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_collection_time': None,
            'last_success_time': None,
            'last_error': None,
            'restart_count': 0,
        }

        self.on_collection_complete: Optional[Callable] = None
        self.on_collection_error: Optional[Callable] = None

        # 전역 예외 핸들러 등록
        self._register_global_exception_handler()

        logger.info("DataCollectionService 초기화 완료")

    # ─────────────────────────────────────────
    # 전역 예외 핸들러
    # ─────────────────────────────────────────
    def _register_global_exception_handler(self):
        """처리되지 않은 예외를 로그로 남기고 프로그램이 죽지 않도록 등록"""

        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logger.critical(
                "처리되지 않은 예외 발생",
                exc_info=(exc_type, exc_value, exc_traceback)
            )

        def handle_thread_exception(args):
            if args.exc_type == SystemExit:
                return
            logger.critical(
                f"스레드 '{args.thread.name}' 처리되지 않은 예외",
                exc_info=(args.exc_type, args.exc_value, args.exc_tb)
            )

        sys.excepthook = handle_exception
        threading.excepthook = handle_thread_exception
        logger.info("전역 예외 핸들러 등록 완료")

    # ─────────────────────────────────────────
    # 시작 / 종료
    # ─────────────────────────────────────────
    def start(self, interval: Optional[int] = None):
        if self._running:
            logger.warning("이미 실행 중입니다.")
            return

        self.interval = interval or self.config.collection_interval
        self._stop_event.clear()
        self._running = True
        self._last_collection_time = time.time()

        # 수집 스레드
        self._thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="DataCollectionService"
        )
        self._thread.start()

        # Watchdog 스레드
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="CollectionWatchdog"
        )
        self._watchdog_thread.start()

        # 외부 재전송 서비스
        self.remote_sync_service.start()

        logger.info(f"DataCollectionService 시작 (주기: {self.interval}초)")
        logger.info("=" * 70)

    def stop(self):
        if not self._running:
            return
        logger.info("DataCollectionService 중지 요청")
        self._stop_event.set()
        self._running = False
        self.remote_sync_service.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("DataCollectionService 중지 완료")

    # ─────────────────────────────────────────
    # 수집 루프
    # ─────────────────────────────────────────
    def _collection_loop(self):
        logger.info("통합 데이터 수집 루프 시작")
        while not self._stop_event.is_set():
            try:
                self._collect_once()
                self._last_collection_time = time.time()
            except Exception as e:
                logger.error(f"수집 루프 오류: {e}", exc_info=True)
                self.stats['last_error'] = str(e)
                if self.on_collection_error:
                    try:
                        self.on_collection_error(str(e))
                    except Exception:
                        pass
            self._stop_event.wait(self.interval)
        logger.info("통합 데이터 수집 루프 종료")

    # ─────────────────────────────────────────
    # Watchdog 루프
    # ─────────────────────────────────────────
    def _watchdog_loop(self):
        """수집 루프가 멈추면 자동 재시작"""
        logger.info("Watchdog 시작")
        while not self._stop_event.is_set():
            time.sleep(30)  # 30초마다 체크
            if not self._running:
                break

            # 수집 스레드 상태 체크
            if self._thread and not self._thread.is_alive():
                if self._restart_count >= MAX_RESTART_COUNT:
                    logger.critical(
                        f"수집 스레드 재시작 횟수 초과 ({MAX_RESTART_COUNT}회). "
                        "수동 점검이 필요합니다."
                    )
                    self.alarm_service.add(
                        'collection_thread_dead',
                        'error',
                        f'데이터 수집 스레드가 {MAX_RESTART_COUNT}회 재시작 후 중단됨 — 수동 점검 필요'
                    )
                    continue

                logger.warning("수집 스레드가 종료됨 — 자동 재시작")
                self._restart_count += 1
                self.stats['restart_count'] = self._restart_count

                self._thread = threading.Thread(
                    target=self._collection_loop,
                    daemon=True,
                    name=f"DataCollectionService_restart{self._restart_count}"
                )
                self._thread.start()
                logger.info(f"수집 스레드 재시작 완료 (#{self._restart_count})")
                self.alarm_service.add(
                    f'collection_restart_{self._restart_count}',
                    'warning',
                    f'데이터 수집 스레드 자동 재시작 (#{self._restart_count})'
                )
                continue

            # 마지막 수집 시간 체크
            if self._last_collection_time:
                elapsed = time.time() - self._last_collection_time
                if elapsed > WATCHDOG_TIMEOUT:
                    logger.warning(
                        f"마지막 수집 후 {elapsed:.0f}초 경과 — 수집 루프 응답 없음"
                    )
                    self.alarm_service.add(
                        'collection_timeout',
                        'warning',
                        f'데이터 수집이 {elapsed/60:.0f}분간 중단됨 — 네트워크 또는 센서 확인 필요'
                    )

        logger.info("Watchdog 종료")

    # ─────────────────────────────────────────
    # 실제 수집
    # ─────────────────────────────────────────
    def _collect_once(self):
        start_time = time.time()

        logger.info("=" * 70)
        logger.info("통합 데이터 수집 시작")
        logger.info("=" * 70)

        self.stats['total_collections'] += 1
        self.stats['last_collection_time'] = datetime.now()

        try:
            # ── 1단계: 전력량계 ──────────────────────
            logger.info("[1/2] 전력량계 데이터 수집")
            try:
                power_meter_data = self.power_meter_service.collector.collect_all()
                power_success = sum(1 for v in power_meter_data.values() if v is not None)
                logger.info(f"전력량계 수집 완료: {power_success}/{len(power_meter_data)}개")
            except Exception as e:
                logger.error(f"전력량계 수집 실패: {e}", exc_info=True)
                power_meter_data = {}
                power_success = 0

            # ── 2단계: 박스 센서 (장치별 독립) ──────
            logger.info("[2/2] 플라스틱 함 센서 데이터 수집")
            try:
                box_results = self.box_sensor_service.collector.collect_all(power_meter_data)
                box_success = (
                    sum(1 for v in box_results['heatpump'].values()
                        if isinstance(v, dict) and v.get('success')) +
                    sum(1 for v in box_results['groundpipe'].values()
                        if isinstance(v, dict) and v.get('success'))
                )
                box_total = (
                    len(box_results['heatpump']) + len(box_results['groundpipe'])
                )
                logger.info(f"플라스틱 함 센서 수집 완료: {box_success}/{box_total}개")
            except Exception as e:
                logger.error(f"박스 센서 수집 실패: {e}", exc_info=True)
                box_results = {'heatpump': {}, 'groundpipe': {}}
                box_success = 0

            # ── DB 연결 풀 상태 체크 ─────────────────
            self._check_db_pool()

            # ── 알림 체크 ────────────────────────────
            try:
                self.alarm_service.check_collection_result({
                    'box_sensor': box_results,
                    'power_meter': power_meter_data
                })
                self.alarm_service.check_queue_size(get_queue_count())

                for device_id, result in box_results.get('heatpump', {}).items():
                    if isinstance(result, dict) and result.get('success'):
                        self.alarm_service.check_flow_zero(
                            device_id, 'heatpump', result.get('flow')
                        )
                for device_id, result in box_results.get('groundpipe', {}).items():
                    if isinstance(result, dict) and result.get('success'):
                        self.alarm_service.check_flow_zero(
                            device_id, 'groundpipe', result.get('flow')
                        )
            except Exception as e:
                logger.error(f"알림 체크 오류: {e}", exc_info=True)

            # ── 통계 ─────────────────────────────────
            total_success = power_success + box_success
            if total_success > 0:
                self.stats['successful_collections'] += 1
                self.stats['last_success_time'] = datetime.now()
                # 수집 성공 시 watchdog 타임아웃 알림 해제
                self.alarm_service.resolve('collection_timeout')
            else:
                self.stats['failed_collections'] += 1

            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info(
                f"수집 완료: 전력량계 {power_success}개, "
                f"박스 센서 {box_success}개, 소요 {elapsed:.2f}초"
            )
            logger.info("=" * 70)

            if self.on_collection_complete:
                try:
                    self.on_collection_complete({
                        'power_meter': power_meter_data,
                        'box_sensor': box_results,
                        'elapsed_time': elapsed
                    })
                except Exception:
                    pass

        except Exception as e:
            self.stats['failed_collections'] += 1
            self.stats['last_error'] = str(e)
            logger.error(f"통합 수집 실패: {e}", exc_info=True)
            if self.on_collection_error:
                try:
                    self.on_collection_error(str(e))
                except Exception:
                    pass

    # ─────────────────────────────────────────
    # DB 연결 풀 자동 복구
    # ─────────────────────────────────────────
    def _check_db_pool(self):
        """DB 연결 풀 상태 확인 및 자동 복구"""
        try:
            from core.database import test_db_connection, initialize_connection_pool
            if not test_db_connection():
                logger.warning("DB 연결 풀 이상 감지 — 재초기화 시도")
                try:
                    initialize_connection_pool()
                    logger.info("DB 연결 풀 재초기화 성공")
                    self.alarm_service.resolve('db_pool_error')
                except Exception as e:
                    logger.error(f"DB 연결 풀 재초기화 실패: {e}")
                    self.alarm_service.add(
                        'db_pool_error', 'error',
                        f'로컬 DB 연결 풀 복구 실패 — 데이터 저장 불가: {e}'
                    )
        except Exception as e:
            logger.error(f"DB 상태 체크 오류: {e}")

    # ─────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────
    def collect_now(self):
        logger.info("수동 수집 트리거")
        threading.Thread(
            target=self._collect_once, daemon=True, name="ManualCollection"
        ).start()

    def is_running(self) -> bool:
        return self._running

    def get_stats(self) -> Dict:
        return self.stats.copy()

    def get_all_stats(self) -> Dict:
        return {
            'integrated': self.get_stats(),
            'power_meter': self.power_meter_service.get_stats(),
            'box_sensor': self.box_sensor_service.get_stats()
        }

    def reload_config(self):
        self.power_meter_service.reload_config()
