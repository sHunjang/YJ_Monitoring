# ==============================================
# 플라스틱 함 센서 서비스
# ==============================================
"""
플라스틱 함 센서 서비스 레이어

주요 기능:
1. 데이터 수집 스케줄링
2. 백그라운드 스레드 관리
3. 수집 통계 및 상태 관리

사용 예:
    from sensors.box.service import BoxSensorService
    
    service = BoxSensorService()
    service.start()  # 수집 시작
    service.stop()   # 수집 중지
"""

import logging
import threading
import time
from typing import Optional, Dict, Callable
from datetime import datetime

from sensors.box.collector import BoxSensorCollector
from core.config import get_config

logger = logging.getLogger(__name__)


class BoxSensorService:
    """
    플라스틱 함 센서 서비스
    
    백그라운드에서 주기적으로 센서 데이터를 수집합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.config = get_config()
        self.collector = BoxSensorCollector()
        
        # 수집 스레드
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
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
        
        logger.info("BoxSensorService 초기화 완료")
    
    def start(self, interval: Optional[int] = None):
        """
        데이터 수집 시작
        
        Args:
            interval: 수집 주기 (초), None이면 설정 파일 값 사용
            
        Example:
            >>> service = BoxSensorService()
            >>> service.start(interval=60)  # 60초마다 수집
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
            name="BoxSensorService"
        )
        self._thread.start()
        
        logger.info(f"BoxSensorService 시작 (주기: {interval}초)")
    
    def stop(self):
        """
        데이터 수집 중지
        
        Example:
            >>> service.stop()
        """
        if not self._running:
            logger.warning("실행 중이 아닙니다.")
            return
        
        logger.info("BoxSensorService 중지 요청")
        
        self._stop_event.set()
        self._running = False
        
        # 스레드 종료 대기
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("BoxSensorService 중지 완료")
    
    def _collection_loop(self):
        """
        데이터 수집 루프 (백그라운드 스레드)
        """
        logger.info("데이터 수집 루프 시작")
        
        while not self._stop_event.is_set():
            try:
                # 데이터 수집 실행
                self._collect_once()
                
            except Exception as e:
                logger.error(f"데이터 수집 루프 오류: {e}", exc_info=True)
                self.stats['last_error'] = str(e)
                
                if self.on_collection_error:
                    try:
                        self.on_collection_error(str(e))
                    except:
                        pass
            
            # 다음 수집까지 대기
            self._stop_event.wait(self.interval)
        
        logger.info("데이터 수집 루프 종료")
    
    def _collect_once(self, power_meter_data: Optional[Dict[str, float]] = None):
        """
        한 번 데이터 수집 실행
        
        Args:
            power_meter_data: 전력량계 데이터 (옵션)
        """
        start_time = time.time()
        
        logger.debug("플라스틱 함 센서 데이터 수집 시작")
        
        # 통계 업데이트
        self.stats['total_collections'] += 1
        self.stats['last_collection_time'] = datetime.now()
        
        try:
            # 데이터 수집
            results = self.collector.collect_all(power_meter_data)
            
            # 성공 여부 확인
            total_success = (
                sum(1 for v in results['heatpump'].values() if v) +
                sum(1 for v in results['groundpipe'].values() if v)
            )
            total_count = len(results['heatpump']) + len(results['groundpipe'])
            
            if total_success > 0:
                self.stats['successful_collections'] += 1
                self.stats['last_success_time'] = datetime.now()
            else:
                self.stats['failed_collections'] += 1
            
            elapsed_time = time.time() - start_time
            
            logger.info(
                f"플라스틱 함 센서 데이터 수집 완료: "
                f"{total_success}/{total_count}개 성공, "
                f"소요 시간: {elapsed_time:.2f}초"
            )
            
            # 콜백 호출 (UI 업데이트)
            if self.on_collection_complete:
                try:
                    self.on_collection_complete(results)
                except:
                    pass
            
        except Exception as e:
            self.stats['failed_collections'] += 1
            self.stats['last_error'] = str(e)
            
            logger.error(f"플라스틱 함 센서 데이터 수집 실패: {e}", exc_info=True)
            
            if self.on_collection_error:
                try:
                    self.on_collection_error(str(e))
                except:
                    pass
    
    def collect_now(self, power_meter_data: Optional[Dict[str, float]] = None):
        """
        즉시 데이터 수집 (수동 트리거)
        
        Args:
            power_meter_data: 전력량계 데이터 (옵션)
            
        Example:
            >>> service.collect_now()
        """
        logger.info("수동 데이터 수집 트리거")
        self._collect_once(power_meter_data)
    
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


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """BoxSensorService 테스트"""
    import sys
    from pathlib import Path
    
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent
    sys.path.insert(0, str(project_root / 'src'))
    
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="INFO")
    
    print("=" * 70)
    print("BoxSensorService 테스트")
    print("=" * 70)
    
    # 데이터베이스 초기화
    initialize_connection_pool()
    
    # Service 생성
    service = BoxSensorService()
    
    # 콜백 설정
    def on_complete(results):
        print("\n✓ 수집 완료 콜백 호출됨")
        print(f"  히트펌프: {len(results['heatpump'])}개")
        print(f"  지중배관: {len(results['groundpipe'])}개")
    
    def on_error(error_msg):
        print(f"\n✗ 오류 콜백 호출됨: {error_msg}")
    
    service.on_collection_complete = on_complete
    service.on_collection_error = on_error
    
    # 즉시 수집 테스트
    print("\n[테스트 1] 즉시 수집")
    service.collect_now()
    
    # 통계 확인
    print("\n[테스트 2] 통계 확인")
    stats = service.get_stats()
    print(f"  총 수집 횟수: {stats['total_collections']}")
    print(f"  성공 횟수: {stats['successful_collections']}")
    print(f"  실패 횟수: {stats['failed_collections']}")
    print(f"  마지막 수집 시간: {stats['last_collection_time']}")
    
    # 백그라운드 수집 테스트
    print("\n[테스트 3] 백그라운드 수집 (10초 간격, 3회)")
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
