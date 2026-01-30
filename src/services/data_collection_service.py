# ==============================================
# 통합 데이터 수집 서비스
# ==============================================
"""
플라스틱 함 센서 + 전력량계 통합 데이터 수집 서비스

주요 기능:
1. 전력량계 먼저 수집
2. 전력량계 데이터를 히트펌프 수집 시 결합
3. 두 서비스의 통합 관리

사용 예:
    from services.data_collection_service import DataCollectionService
    
    service = DataCollectionService()
    service.start()  # 모든 센서 수집 시작
    service.stop()   # 모든 센서 수집 중지
"""

import logging
import threading
import time
from typing import Optional, Dict, Callable
from datetime import datetime

from sensors.box.service import BoxSensorService
from sensors.power.service import PowerMeterService
from core.config import get_config

logger = logging.getLogger(__name__)


class DataCollectionService:
    """
    통합 데이터 수집 서비스
    
    플라스틱 함 센서와 전력량계를 통합 관리합니다.
    전력량계 데이터를 먼저 수집하고, 이를 히트펌프 수집 시 활용합니다.
    """
    
    def __init__(self):
        """초기화"""
        self.config = get_config()
        
        # 서비스 인스턴스
        self.power_meter_service = PowerMeterService()
        self.box_sensor_service = BoxSensorService()
        
        # 통합 수집 스레드
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
        
        # 콜백 함수
        self.on_collection_complete: Optional[Callable] = None
        self.on_collection_error: Optional[Callable] = None
        
        logger.info("DataCollectionService 초기화 완료")
    
    def start(self, interval: Optional[int] = None):
        """
        통합 데이터 수집 시작
        
        Args:
            interval: 수집 주기 (초), None이면 설정 파일 값 사용
            
        Example:
            >>> service = DataCollectionService()
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
            name="DataCollectionService"
        )
        self._thread.start()
        
        logger.info(f"DataCollectionService 시작 (주기: {interval}초)")
        logger.info("=" * 70)
    
    def stop(self):
        """
        통합 데이터 수집 중지
        
        Example:
            >>> service.stop()
        """
        if not self._running:
            logger.warning("실행 중이 아닙니다.")
            return
        
        logger.info("DataCollectionService 중지 요청")
        
        self._stop_event.set()
        self._running = False
        
        # 스레드 종료 대기
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("DataCollectionService 중지 완료")
    
    def _collection_loop(self):
        """데이터 수집 루프 (백그라운드 스레드)"""
        logger.info("통합 데이터 수집 루프 시작")
        
        while not self._stop_event.is_set():
            try:
                # 데이터 수집 실행
                self._collect_once()
                
            except Exception as e:
                logger.error(f"통합 데이터 수집 루프 오류: {e}", exc_info=True)
                self.stats['last_error'] = str(e)
                
                if self.on_collection_error:
                    try:
                        self.on_collection_error(str(e))
                    except:
                        pass
            
            # 다음 수집까지 대기
            self._stop_event.wait(self.interval)
        
        logger.info("통합 데이터 수집 루프 종료")
    
    def _collect_once(self):
        """
        한 번 통합 데이터 수집 실행
        
        수집 순서:
        1. 전력량계 데이터 수집
        2. 플라스틱 함 센서 수집 (전력량계 데이터 포함)
        """
        start_time = time.time()
        
        logger.info("=" * 70)
        logger.info("통합 데이터 수집 시작")
        logger.info("=" * 70)
        
        # 통계 업데이트
        self.stats['total_collections'] += 1
        self.stats['last_collection_time'] = datetime.now()
        
        try:
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1단계: 전력량계 데이터 수집
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            logger.info("[1/2] 전력량계 데이터 수집")
            
            power_meter_data = self.power_meter_service.collector.collect_all()
            
            power_success = sum(1 for v in power_meter_data.values() if v is not None)
            logger.info(f"전력량계 수집 완료: {power_success}/{len(power_meter_data)}개")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2단계: 플라스틱 함 센서 수집 (전력량계 데이터 포함)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            logger.info("[2/2] 플라스틱 함 센서 데이터 수집")
            
            box_results = self.box_sensor_service.collector.collect_all(power_meter_data)
            
            box_success = (
                sum(1 for v in box_results['heatpump'].values() if v) +
                sum(1 for v in box_results['groundpipe'].values() if v)
            )
            box_total = len(box_results['heatpump']) + len(box_results['groundpipe'])
            
            logger.info(f"플라스틱 함 센서 수집 완료: {box_success}/{box_total}개")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 통계 업데이트
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            total_success = power_success + box_success
            
            if total_success > 0:
                self.stats['successful_collections'] += 1
                self.stats['last_success_time'] = datetime.now()
            else:
                self.stats['failed_collections'] += 1
            
            elapsed_time = time.time() - start_time
            
            logger.info("=" * 70)
            logger.info(
                f"통합 데이터 수집 완료: "
                f"전력량계 {power_success}개, "
                f"플라스틱 함 {box_success}개, "
                f"소요 시간: {elapsed_time:.2f}초"
            )
            logger.info("=" * 70)
            
            # 콜백 호출 (UI 업데이트)
            if self.on_collection_complete:
                try:
                    result = {
                        'power_meter': power_meter_data,
                        'box_sensor': box_results,
                        'elapsed_time': elapsed_time
                    }
                    self.on_collection_complete(result)
                except:
                    pass
            
        except Exception as e:
            self.stats['failed_collections'] += 1
            self.stats['last_error'] = str(e)
            
            logger.error(f"통합 데이터 수집 실패: {e}", exc_info=True)
            
            if self.on_collection_error:
                try:
                    self.on_collection_error(str(e))
                except:
                    pass
    
    def collect_now(self):
        """
        즉시 통합 데이터 수집 (수동 트리거)
        
        Example:
            >>> service.collect_now()
        """
        logger.info("수동 통합 데이터 수집 트리거")
        self._collect_once()
    
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
    
    def get_all_stats(self) -> Dict:
        """
        모든 서비스의 통계 정보 반환
        
        Returns:
            dict: {
                'integrated': {...},
                'power_meter': {...},
                'box_sensor': {...}
            }
        """
        return {
            'integrated': self.get_stats(),
            'power_meter': self.power_meter_service.get_stats(),
            'box_sensor': self.box_sensor_service.get_stats()
        }
    
    def reset_stats(self):
        """모든 통계 초기화"""
        self.stats = {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_collection_time': None,
            'last_success_time': None,
            'last_error': None
        }
        self.power_meter_service.reset_stats()
        self.box_sensor_service.reset_stats()
        logger.info("모든 통계 초기화")
    
    def reload_config(self):
        """
        설정 파일 다시 로드
        
        사용자가 설정을 변경한 후 호출합니다.
        """
        logger.info("설정 다시 로드")
        self.power_meter_service.reload_config()
        # box_sensor_service는 매번 설정을 읽으므로 reload 불필요
    
    def get_latest_power_meter_data(self) -> Optional[Dict[str, float]]:
        """
        최신 전력량계 데이터 조회
        
        Returns:
            dict: {device_id: energy (kWh)}
        """
        return self.power_meter_service.get_latest_data()


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """DataCollectionService 테스트"""
    import sys
    from pathlib import Path
    
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    sys.path.insert(0, str(project_root / 'src'))
    
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="INFO")
    
    print("=" * 70)
    print("DataCollectionService 테스트")
    print("=" * 70)
    
    # 데이터베이스 초기화
    initialize_connection_pool()
    
    # Service 생성
    service = DataCollectionService()
    
    # 콜백 설정
    def on_complete(result):
        print("\n✓ 통합 수집 완료 콜백")
        print(f"  전력량계: {len(result['power_meter'])}개")
        print(f"  히트펌프: {len(result['box_sensor']['heatpump'])}개")
        print(f"  지중배관: {len(result['box_sensor']['groundpipe'])}개")
        print(f"  소요 시간: {result['elapsed_time']:.2f}초")
    
    def on_error(error_msg):
        print(f"\n✗ 오류 콜백: {error_msg}")
    
    service.on_collection_complete = on_complete
    service.on_collection_error = on_error
    
    # 즉시 수집 테스트
    print("\n[테스트 1] 즉시 통합 수집")
    service.collect_now()
    
    # 통계 확인
    print("\n[테스트 2] 통계 확인")
    all_stats = service.get_all_stats()
    
    print("  통합 서비스:")
    print(f"    총 수집: {all_stats['integrated']['total_collections']}")
    print(f"    성공: {all_stats['integrated']['successful_collections']}")
    
    print("  전력량계 서비스:")
    print(f"    총 수집: {all_stats['power_meter']['total_collections']}")
    
    print("  플라스틱 함 서비스:")
    print(f"    총 수집: {all_stats['box_sensor']['total_collections']}")
    
    # 백그라운드 수집 테스트
    print("\n[테스트 3] 백그라운드 수집 (30초 간격, 2회)")
    service.start(interval=30)
    
    print("  실행 중... (60초 대기)")
    time.sleep(60)
    
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
