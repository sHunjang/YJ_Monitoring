# ==============================================
# 알림 서비스
# ==============================================
"""
센서 데이터 수집 결과 기반 알림 관리

알림 조건:
- 히트펌프/지중배관 유량 = 0
- 센서 데이터 수집 실패
- 원격 DB 연결 끊김
- 재전송 큐 50건 초과

중복 알림 방지: 같은 key로 발생한 알림은 해제될 때까지 재발생 안 함
"""

import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class AlarmItem:
    """알림 항목"""

    def __init__(self, key: str, level: str, message: str):
        """
        Args:
            key:     중복 방지용 고유 키 (예: 'HP_1_flow_zero')
            level:   'warning' | 'error'
            message: 표시할 메시지
        """
        self.key       = key
        self.level     = level
        self.message   = message
        self.timestamp = datetime.now()
        self.is_active = True

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.message}"


class AlarmService:
    """알림 서비스 (싱글톤)"""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        # 활성 알림 {key: AlarmItem}
        self._alarms: Dict[str, AlarmItem] = {}
        self._alarms_lock = threading.Lock()

        # 새 알림 발생 시 호출할 콜백 (UI에서 등록)
        self.on_alarm_added: Optional[callable] = None

        logger.info("AlarmService 초기화 완료")

    @classmethod
    def get_instance(cls) -> 'AlarmService':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ─────────────────────────────────────────────
    # 알림 추가 / 해제
    # ─────────────────────────────────────────────
    def add(self, key: str, level: str, message: str):
        """
        알림 추가 (같은 key면 중복 추가 안 함)

        Args:
            key:     고유 키
            level:   'warning' | 'error'
            message: 표시 메시지
        """
        with self._alarms_lock:
            if key in self._alarms:
                return  # 중복 무시

            item = AlarmItem(key, level, message)
            self._alarms[key] = item
            logger.warning(f"🔔 알림 발생: {message}")

        # 알림음 + 콜백 (lock 밖에서)
        self._play_sound()
        if self.on_alarm_added:
            try:
                self.on_alarm_added(item)
            except Exception:
                pass

    def resolve(self, key: str):
        """알림 해제 (정상 복구 시 호출)"""
        with self._alarms_lock:
            if key in self._alarms:
                del self._alarms[key]
                logger.info(f"✓ 알림 해제: {key}")

    def resolve_all(self):
        """전체 알림 해제"""
        with self._alarms_lock:
            self._alarms.clear()

    # ─────────────────────────────────────────────
    # 조회
    # ─────────────────────────────────────────────
    def get_all(self) -> List[AlarmItem]:
        """전체 알림 목록 반환 (최신순)"""
        with self._alarms_lock:
            items = list(self._alarms.values())
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items

    def count(self) -> int:
        """현재 활성 알림 수"""
        with self._alarms_lock:
            return len(self._alarms)

    def has_alarm(self, key: str) -> bool:
        """특정 key 알림이 있는지 확인"""
        with self._alarms_lock:
            return key in self._alarms

    # ─────────────────────────────────────────────
    # 알림음
    # ─────────────────────────────────────────────
    def _play_sound(self):
        """윈도우 기본 알림음"""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass  # 윈도우 외 환경에서는 무시

    # ─────────────────────────────────────────────
    # 수집 결과 기반 알림 체크
    # ─────────────────────────────────────────────
    def check_collection_result(self, results: dict):
        """
        데이터 수집 결과를 받아 알림 조건 체크

        Args:
            results: DataCollectionService._collect_once()의 결과
                {
                    'box_sensor': {
                        'heatpump':  {device_id: bool},
                        'groundpipe': {device_id: bool}
                    },
                    'power_meter': {device_id: PowerMeterData | None}
                }
        """
        box = results.get('box_sensor', {})

        # 히트펌프 수집 실패
        for device_id, result in box.get('heatpump', {}).items():
            key = f'{device_id}_collect_fail'
            if not result.get('success'):
                self.add(key, 'error', f'[히트펌프] {device_id} 데이터 수집 실패')
            else:
                self.resolve(key)

        for device_id, result in box.get('groundpipe', {}).items():
            key = f'{device_id}_collect_fail'
            if not result.get('success'):
                self.add(key, 'error', f'[지중배관] {device_id} 데이터 수집 실패')
            else:
                self.resolve(key)

    def check_queue_size(self, queue_count: int):
        """재전송 큐 크기 알림 체크"""
        key = 'remote_queue_overflow'
        if queue_count >= 50:
            self.add(key, 'warning',
                     f'재전송 대기 큐 {queue_count}건 — 원격 DB 연결을 확인하세요')
        else:
            self.resolve(key)

    def check_remote_db(self, is_connected: bool):
        """원격 DB 연결 상태 알림 체크"""
        key = 'remote_db_disconnected'
        if not is_connected:
            self.add(key, 'warning',
                     '원격 DB 연결 끊김 — 데이터는 로컬에 저장 중입니다')
        else:
            self.resolve(key)

    def check_flow_zero(self, device_id: str, device_type: str, flow: float):
        """
        유량 0 알림 체크

        Args:
            device_id:   장치 ID
            device_type: 'heatpump' | 'groundpipe'
            flow:        유량값
        """
        key = f'{device_id}_flow_zero'
        type_kr = '히트펌프' if device_type == 'heatpump' else '지중배관'
        if flow is not None and flow == 0:
            self.add(key, 'warning',
                     f'[{type_kr}] {device_id} 유량 0 — 센서 또는 배관 확인 필요')
        else:
            self.resolve(key)