# ==============================================
# 전력량계 서비스
# ==============================================
"""
전력량계 서비스 레이어

주요 기능:
1. 데이터 수집 스케줄링
2. 백그라운드 스레드 관리
3. 수집 통계 및 상태 관리

사용 예:
    from sensors.power.service import PowerMeterService
    
    service = PowerMeterService()
    service.start()  # 수집 시작
    data = service.get_latest_data()  # 최신 데이터 조회
"""

import logging
import threading
import time
from typing import Optional, Dict, Callable
from datetime import datetime

from sensors.power.collector import PowerMeterCollector
from core.config import get_config

logger = logging.getLogger(__name__)


class PowerMeterService:
    """
    전력량계 서비스
    
    백그라운드에서 주기적으로 전력량계 데이터를 수집합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.config = get_config()
        self.collector = PowerMeterCollector()
        
        # 수집 스레드
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # 최신 데이터 캐시
        self._latest_data: Optional[Dict[str, float]] = None
        self._data_lock = threading.Lock()
        
        # 통계
        self.stats = {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_collection_time': None,
            'last_success_time': None,
            'last_error': None
        }
        
        # 콜백 함수 (UI 업데이트용)
        self.on_collection_complete: Optional[Callable] = None
        self.on_collection_error: Optional[Callable] = None
        
        logger.info("PowerMeterService 초기화 완료")
    
    def start(self, interval: Optional[int] = None):
        """
        데이터 수집 시작
        
        Args:
            interval: 수집 주기 (초), None이면 설정 파일 값 사용
        """
        if self._running:
            logger.warning("이미 실행 중입니다.")
            return
        
        # 수집 주기 설정
        if interval is None:
            interval = self.config.collection_interval
        
        self.interval = interval
        
        # 스레드 시작
        self._stop_event.clear()
        self._running = True
        
        self._thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="PowerMeterService"
        )
        self._thread.start()
        
        logger.info(f"PowerMeterService 시작 (주기: {interval}초)")
    
    def stop(self):
        """데이터 수집 중지"""
        if not self._running:
            logger.warning("실행 중이 아닙니다.")
            return
        
        logger.info("PowerMeterService 중지 요청")
        
        self._stop_event.set()
        self._running = False
        
        # 스레드 종료 대기
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("PowerMeterService 중지 완료")
    
    def _collection_loop(self):
        """데이터 수집 루프 (백그라운드 스레드)"""
        logger.info("전력량계 수집 루프 시작")
        
        while not self._stop_event.is_set():
            try:
                # 데이터 수집 실행
                self._collect_once()
                
            except Exception as e:
                logger.error(f"전력량계 수집 루프 오류: {e}", exc_info=True)
                self.stats['last_error'] = str(e)
                
                if self.on_collection_error:
                    try:
                        self.on_collection_error(str(e))
                    except:
                        pass
            
            # 다음 수집까지 대기
            self._stop_event.wait(self.interval)
        
        logger.info("전력량계 수집 루프 종료")
    
    def _collect_once(self):
        """한 번 데이터 수집 실행"""
        start_time = time.time()
        
        logger.debug("전력량계 데이터 수집 시작")
        
        # 통계 업데이트
        self.stats['total_collections'] += 1
        self.stats['last_collection_time'] = datetime.now()
        
        try:
            # 데이터 수집
            data = self.collector.collect_all()
            
            # 최신 데이터 캐시 업데이트
            with self._data_lock:
                self._latest_data = data
            
            # 성공 여부 확인
            success_count = sum(1 for v in data.values() if v is not None)
            
            if success_count > 0:
                self.stats['successful_collections'] += 1
                self.stats['last_success_time'] = datetime.now()
            else:
                self.stats['failed_collections'] += 1
            
            elapsed_time = time.time() - start_time
            
            logger.info(
                f"전력량계 데이터 수집 완료: "
                f"{success_count}/{len(data)}개 성공, "
                f"소요 시간: {elapsed_time:.2f}초"
            )
            
            # 콜백 호출 (UI 업데이트)
            if self.on_collection_complete:
                try:
                    self.on_collection_complete(data)
                except:
                    pass
            
        except Exception as e:
            self.stats['failed_collections'] += 1
            self.stats['last_error'] = str(e)
            
            logger.error(f"전력량계 데이터 수집 실패: {e}", exc_info=True)
            
            if self.on_collection_error:
                try:
                    self.on_collection_error(str(e))
                except:
                    pass
    
    def collect_now(self):
        """
        즉시 데이터 수집 (수동 트리거)
        
        Example:
            >>> service.collect_now()
        """
        logger.info("수동 전력량계 데이터 수집 트리거")
        self._collect_once()
    
    def get_latest_data(self) -> Optional[Dict[str, float]]:
        """
        최신 수집 데이터 조회
        
        Returns:
            dict: {device_id: energy (kWh)}
            None: 아직 수집된 데이터 없음
            
        Example:
            >>> data = service.get_latest_data()
            >>> if data:
            >>>     print(data['HP_1'])
        """
        with self._data_lock:
            return self._latest_data.copy() if self._latest_data else None
    
    def is_running(self) -> bool:
        """
        실행 중인지 확인
        
        Returns:
            bool: 실행 중이면 True
        """
        return self._running
    
    def get_stats(self) -> Dict:
        """
        통계 정보 반환
        
        Returns:
            dict: 통계 정보
        """
        return self.stats.copy()
    
    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_collection_time': None,
            'last_success_time': None,
            'last_error': None
        }
        logger.info("통계 초기화")
    
    def reload_config(self):
        """
        설정 파일 다시 로드
        
        사용자가 전력량계 설정을 변경한 후 호출합니다.
        """
        logger.info("전력량계 설정 다시 로드")
        self.collector.reload_config()


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """PowerMeterService 테스트"""
    import sys
    from pathlib import Path
    
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent
    sys.path.insert(0, str(project_root / 'src'))
    
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="INFO")
    
    print("=" * 70)
    print("PowerMeterService 테스트")
    print("=" * 70)
    
    # 데이터베이스 초기화
    initialize_connection_pool()
    
    # Service 생성
    service = PowerMeterService()
    
    # 콜백 설정
    def on_complete(data):
        print("\n✓ 수집 완료 콜백 호출됨")
        print(f"  수집된 전력량계: {len(data)}개")
        for device_id, energy in list(data.items())[:3]:
            print(f"    - {device_id}: {energy} kWh")
    
    def on_error(error_msg):
        print(f"\n✗ 오류 콜백 호출됨: {error_msg}")
    
    service.on_collection_complete = on_complete
    service.on_collection_error = on_error
    
    # 즉시 수집 테스트
    print("\n[테스트 1] 즉시 수집")
    service.collect_now()
    
    # 최신 데이터 조회
    print("\n[테스트 2] 최신 데이터 조회")
    latest_data = service.get_latest_data()
    if latest_data:
        print(f"  총 {len(latest_data)}개 전력량계")
    else:
        print("  데이터 없음")
    
    # 통계 확인
    print("\n[테스트 3] 통계 확인")
    stats = service.get_stats()
    print(f"  총 수집 횟수: {stats['total_collections']}")
    print(f"  성공 횟수: {stats['successful_collections']}")
    print(f"  실패 횟수: {stats['failed_collections']}")
    
    # 백그라운드 수집 테스트
    print("\n[테스트 4] 백그라운드 수집 (10초 간격, 3회)")
    service.start(interval=10)
    
    print("  실행 중... (30초 대기)")
    time.sleep(30)
    
    service.stop()
    
    # 최종 통계
    print("\n[최종 통계]")
    stats = service.get_stats()
    print(f"  총 수집 횟수: {stats['total_collections']}")
    print(f"  성공 횟수: {stats['successful_collections']}")
    print(f"  실패 횟수: {stats['failed_collections']}")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
