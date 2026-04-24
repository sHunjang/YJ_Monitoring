# ==============================================
# 외부 DB 재전송 서비스
# ==============================================
"""
로컬 큐에 쌓인 데이터를 외부 DB로 재전송하는 백그라운드 서비스

동작:
- 30초마다 remote_send_queue 테이블 확인
- 외부 DB가 살아있으면 순서대로 재전송
- 성공 시 큐에서 삭제, 실패 시 retry_count 증가
- retry_count가 MAX_RETRY 초과 시 해당 항목 폐기 (로그 기록)
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Optional

import psycopg2

from core.config import get_config
from core.database import (
    get_queue_items, delete_queue_item,
    update_queue_retry, get_queue_count
)

logger = logging.getLogger(__name__)

MAX_RETRY    = 20    # 최대 재시도 횟수 초과 시 폐기
SYNC_INTERVAL = 15  # 재전송 주기 (초)

# 테이블별 INSERT 쿼리
REMOTE_QUERIES = {
    'heatpump': """
        INSERT INTO heatpump (device_id, timestamp, input_temp, output_temp, flow, energy)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """,
    'groundpipe': """
        INSERT INTO groundpipe (device_id, timestamp, input_temp, output_temp, flow)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """,
    'elec': """
        INSERT INTO elec (device_id, timestamp, total_energy)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """,
}


class RemoteSyncService:
    """외부 DB 재전송 백그라운드 서비스"""

    def __init__(self):
        self.config = get_config()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._remote_conn = None
        logger.info("RemoteSyncService 초기화 완료")

    def start(self):
        if not self.config.db_remote_enabled:
            logger.info("외부 DB 비활성화 상태 — RemoteSyncService 시작 안 함")
            return

        if self._running:
            logger.warning("RemoteSyncService 이미 실행 중")
            return

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="RemoteSyncService"
        )
        self._thread.start()
        logger.info(f"RemoteSyncService 시작 (주기: {SYNC_INTERVAL}초)")

    def stop(self):
        if not self._running:
            return
        logger.info("RemoteSyncService 중지 요청")
        self._stop_event.set()
        self._running = False
        self._close_remote_conn()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("RemoteSyncService 중지 완료")

    def is_running(self) -> bool:
        return self._running

    # ─────────────────────────────────────────────
    # 외부 연결 관리
    # ─────────────────────────────────────────────
    def _get_remote_conn(self):
        """외부 DB 연결 가져오기 (재연결 포함)"""
        try:
            if self._remote_conn is None or self._remote_conn.closed:
                self._remote_conn = psycopg2.connect(
                    host=self.config.db_remote_host,
                    port=self.config.db_remote_port,
                    database=self.config.db_remote_name,
                    user=self.config.db_remote_user,
                    password=self.config.db_remote_password,
                    connect_timeout=5
                )
                logger.info("외부 DB 재연결 성공")
            return self._remote_conn
        except Exception as e:
            logger.warning(f"외부 DB 연결 실패: {e}")
            self._remote_conn = None
            return None

    def _close_remote_conn(self):
        if self._remote_conn:
            try:
                self._remote_conn.close()
            except Exception:
                pass
            self._remote_conn = None

    # ─────────────────────────────────────────────
    # 재전송 루프
    # ─────────────────────────────────────────────
    def _sync_loop(self):
        logger.info("외부 DB 재전송 루프 시작")
        while not self._stop_event.is_set():
            try:
                queue_count = get_queue_count()
                if queue_count > 0:
                    logger.info(f"재전송 큐 {queue_count}건 처리 시작")
                    self._process_queue()
            except Exception as e:
                logger.error(f"재전송 루프 오류: {e}", exc_info=True)

            self._stop_event.wait(SYNC_INTERVAL)
        logger.info("외부 DB 재전송 루프 종료")

    def _process_queue(self):
        """큐 항목 배치로 재전송 처리"""
        items = get_queue_items(limit=50)
        if not items:
            return

        conn = self._get_remote_conn()
        if conn is None:
            logger.warning("외부 DB 연결 불가 — 재전송 다음 주기로 연기")
            return

        # ── 최대 재시도 초과 항목 먼저 폐기 ──────────
        discard_ids = []
        send_items  = []
        for item in items:
            if item['retry_count'] >= MAX_RETRY:
                logger.error(
                    f"큐 항목 폐기 (최대 재시도 초과): "
                    f"id={item['id']}, table={item['table_name']}, "
                    f"created_at={item['created_at']}"
                )
                discard_ids.append(item['id'])
            else:
                send_items.append(item)

        for item_id in discard_ids:
            delete_queue_item(item_id)

        if not send_items:
            return

        # ── 테이블별로 묶어서 배치 전송 ───────────────
        from collections import defaultdict
        grouped = defaultdict(list)  # {table_name: [item, ...]}
        for item in send_items:
            grouped[item['table_name']].append(item)

        success_ids = []
        fail_ids    = []

        for table_name, group in grouped.items():
            query = REMOTE_QUERIES.get(table_name)
            if query is None:
                logger.error(f"알 수 없는 테이블명: {table_name}")
                for item in group:
                    fail_ids.append(item['id'])
                continue

            # 파라미터 파싱
            batch_params = []
            batch_ids    = []
            for item in group:
                params = self._parse_params(item)
                if params is not None:
                    batch_params.append(params)
                    batch_ids.append(item['id'])
                else:
                    fail_ids.append(item['id'])

            if not batch_params:
                continue

            # executemany로 배치 전송
            try:
                cursor = conn.cursor()
                cursor.executemany(query, batch_params)
                conn.commit()
                cursor.close()
                success_ids.extend(batch_ids)
                logger.debug(f"[{table_name}] 배치 전송 성공: {len(batch_ids)}건")

            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                logger.warning(f"[{table_name}] 배치 전송 실패: {e}")
                self._remote_conn = None
                fail_ids.extend(batch_ids)

        # ── 결과 반영 ──────────────────────────────────
        for item_id in success_ids:
            delete_queue_item(item_id)

        for item_id in fail_ids:
            update_queue_retry(item_id)

        if success_ids or fail_ids:
            logger.info(
                f"재전송 완료 — 성공: {len(success_ids)}건, "
                f"실패: {len(fail_ids)}건"
            )

    def _parse_params(self, item: dict):
        """큐 항목의 payload를 파라미터 튜플로 변환"""
        try:
            raw = item['payload']
            params_list = json.loads(raw) if isinstance(raw, str) else list(raw)

            params = []
            for v in params_list:
                if isinstance(v, str):
                    try:
                        params.append(datetime.fromisoformat(v))
                    except ValueError:
                        params.append(v)
                else:
                    params.append(v)
            return tuple(params)

        except Exception as e:
            logger.error(f"payload 파싱 실패 (id={item['id']}): {e}")
            return None