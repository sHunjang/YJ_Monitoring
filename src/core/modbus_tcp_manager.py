# ==============================================
# Modbus TCP 연결 관리자 (연결 풀 패턴)
# ==============================================
"""
Modbus RTU over TCP 연결 관리

이 모듈은 Modbus RTU over TCP 연결을 효율적으로 관리합니다.
(Hercules 등 Raw TCP 기반 Modbus 장비와 통신)

주요 기능:
1. 연결 풀 관리 (IP:Port별로 연결 재사용)
2. 자동 재연결
3. 스레드 안전성 (Lock)
4. 싱글톤 패턴
5. Modbus RTU Framer 사용 (CRC 포함)

사용 예:
    manager = ModbusTcpManager.get_instance()
    client = manager.get_client('192.168.0.81', 8899)
    
    with manager.get_lock('192.168.0.81', 8899):
        result = client.read_holding_registers(...)
"""
import logging
import threading
import time
from typing import Dict, Optional, Tuple
from pymodbus.client import ModbusTcpClient
try:
    from pymodbus.framer import ModbusRtuFramer
except ImportError:
    from pymodbus.framer import FramerRTU as ModbusRtuFramer

from core.config import get_config

logger = logging.getLogger(__name__)

# Circuit Breaker 설정
FAILURE_THRESHOLD = 3      # 연속 실패 N회 → 차단
RECOVERY_TIMEOUT  = 30.0   # 차단 후 재시도까지 대기 시간(초)
CONNECT_TIMEOUT   = 2.0    # 연결 타임아웃 (기존 3초 → 2초)


class _ConnectionState:
    """IP:Port 단위 연결 상태 관리"""

    CLOSED   = 'closed'    # 연결 안 됨
    OPEN     = 'open'      # 정상 연결
    BREAKING = 'breaking'  # Circuit Breaker 차단 중

    def __init__(self):
        self.client: Optional[ModbusTcpClient] = None
        self.lock   = threading.Lock()
        self.status = self.CLOSED

        # Circuit Breaker
        self.fail_count     = 0
        self.last_fail_time = 0.0

    def is_circuit_open(self) -> bool:
        """차단 중이면 True (수집 스킵)"""
        if self.status != self.BREAKING:
            return False
        # 차단 시간이 지났으면 재시도 허용
        if time.time() - self.last_fail_time >= RECOVERY_TIMEOUT:
            logger.info(f"Circuit Breaker 재시도 허용")
            self.status = self.CLOSED
            self.fail_count = 0
            return False
        return True

    def record_failure(self, key: str):
        self.fail_count += 1
        self.last_fail_time = time.time()
        if self.fail_count >= FAILURE_THRESHOLD:
            self.status = self.BREAKING
            logger.warning(
                f"[{key}] Circuit Breaker 차단 "
                f"(연속 {self.fail_count}회 실패, "
                f"{RECOVERY_TIMEOUT}초 후 재시도)"
            )

    def record_success(self):
        self.fail_count = 0
        self.status = self.OPEN


class ModbusTcpManager:
    """
    Modbus RTU over TCP 연결 관리자 (싱글톤)

    개선 사항:
    - Circuit Breaker 패턴: 연속 실패 장치 일시 차단
    - 연결 타임아웃 단축: 2초
    - 장치별 독립 Lock: 한 IP 재연결이 다른 IP에 영향 없음
    - 자동 재연결: 차단 해제 후 자동 복구
    """

    _instance  = None
    _init_lock = threading.Lock()

    def __init__(self):
        if ModbusTcpManager._instance is not None:
            raise Exception("싱글톤 클래스입니다. get_instance()를 사용하세요.")

        self.config = get_config()
        self.timeout = CONNECT_TIMEOUT

        # {connection_key: _ConnectionState}
        self._states: Dict[str, _ConnectionState] = {}
        self._pool_lock = threading.Lock()  # 풀 딕셔너리 자체 보호용

        logger.info("=" * 70)
        logger.info("ModbusTcpManager 초기화 (RTU over TCP, Circuit Breaker 적용)")
        logger.info("=" * 70)
        logger.info(f"  연결 타임아웃  : {self.timeout}초")
        logger.info(f"  차단 임계값    : {FAILURE_THRESHOLD}회 연속 실패")
        logger.info(f"  차단 해제 시간 : {RECOVERY_TIMEOUT}초")
        logger.info("=" * 70)

    @classmethod
    def get_instance(cls) -> 'ModbusTcpManager':
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_or_create_state(self, key: str) -> _ConnectionState:
        """연결 상태 객체 가져오기 (없으면 생성)"""
        with self._pool_lock:
            if key not in self._states:
                self._states[key] = _ConnectionState()
            return self._states[key]

    def get_client(self, ip: str, port: int = 502) -> Optional[ModbusTcpClient]:
        """
        Modbus 클라이언트 반환.
        Circuit Breaker 차단 중이면 즉시 None 반환 (타임아웃 없음).
        """
        key   = f"{ip}:{port}"
        state = self._get_or_create_state(key)

        # Circuit Breaker 차단 중 → 즉시 스킵 (다른 장치에 영향 없음)
        if state.is_circuit_open():
            remain = RECOVERY_TIMEOUT - (time.time() - state.last_fail_time)
            logger.debug(f"[{key}] Circuit Breaker 차단 중 (남은 시간: {remain:.0f}초)")
            return None

        # 장치별 Lock — 같은 IP를 여러 스레드가 동시에 재연결 시도하지 않도록
        with state.lock:
            # 이미 연결된 경우
            if state.client and state.client.connected:
                return state.client

            # 끊어진 연결 정리
            if state.client:
                try:
                    state.client.close()
                except Exception:
                    pass
                state.client = None

            # 재연결 시도
            logger.info(f"[{key}] 연결 시도...")
            try:
                client = ModbusTcpClient(
                    host=ip,
                    port=port,
                    timeout=self.timeout,
                    framer=ModbusRtuFramer
                )
                if client.connect():
                    state.client = client
                    state.record_success()
                    state.status = _ConnectionState.OPEN
                    logger.info(f"✓ [{key}] 연결 성공")
                    return client
                else:
                    state.record_failure(key)
                    logger.error(f"✗ [{key}] 연결 실패")
                    return None

            except Exception as e:
                state.record_failure(key)
                logger.error(f"✗ [{key}] 연결 오류: {e}")
                return None

    def record_read_success(self, ip: str, port: int = 502):
        """읽기 성공 시 호출 — Circuit Breaker 실패 카운터 리셋"""
        key = f"{ip}:{port}"
        state = self._get_or_create_state(key)
        state.record_success()

    def record_read_failure(self, ip: str, port: int = 502):
        """읽기 실패 시 호출 — Circuit Breaker 카운터 증가"""
        key = f"{ip}:{port}"
        state = self._get_or_create_state(key)
        with self._pool_lock:
            state.record_failure(key)

    def get_lock(self, ip: str, port: int = 502) -> threading.Lock:
        """특정 연결의 Lock 반환"""
        key   = f"{ip}:{port}"
        state = self._get_or_create_state(key)
        return state.lock

    def is_connected(self, ip: str, port: int = 502) -> bool:
        key = f"{ip}:{port}"
        with self._pool_lock:
            if key in self._states:
                s = self._states[key]
                return s.client is not None and s.client.connected
        return False

    @property
    def clients(self) -> dict:
        """기존 코드 호환용 — {key: client} 형태로 반환"""
        with self._pool_lock:
            return {
                k: s.client
                for k, s in self._states.items()
                if s.client is not None
            }

    def get_all_status(self) -> Dict[str, dict]:
        """전체 연결 상태 조회 (모니터링용)"""
        with self._pool_lock:
            result = {}
            for key, state in self._states.items():
                result[key] = {
                    'connected':  state.client.connected if state.client else False,
                    'status':     state.status,
                    'fail_count': state.fail_count,
                }
            return result

    def close_all(self):
        """모든 연결 종료"""
        with self._pool_lock:
            for key, state in self._states.items():
                try:
                    if state.client:
                        state.client.close()
                        logger.debug(f"[{key}] 연결 종료")
                except Exception as e:
                    logger.error(f"[{key}] 연결 종료 오류: {e}")
            self._states.clear()
        logger.info("✓ 모든 Modbus 연결 종료")

    def __del__(self):
        self.close_all()