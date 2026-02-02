# ==============================================
# UI 데이터 서비스
# ==============================================
"""
GUI에서 사용할 데이터베이스 조회 서비스

기능:
- 센서 목록 조회
- 시계열 데이터 조회
- 통계 데이터 계산
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.database import execute_query

logger = logging.getLogger(__name__)


class UIDataService:
    """UI 데이터 서비스 클래스"""
    
    def __init__(self):
        """초기화"""
        logger.info("UIDataService 초기화")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 센서 목록 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_all_heatpump_devices(self) -> List[str]:
        """
        모든 히트펌프 장치 ID 조회
        
        Returns:
            List[str]: 장치 ID 리스트 (예: ['HP_1', 'HP_2', ...])
        """
        try:
            query = """
                SELECT DISTINCT device_id
                FROM heatpump
                ORDER BY device_id
            """
            result = execute_query(query, fetch_mode='all')
            return [row['device_id'] for row in result]
        except Exception as e:
            logger.error(f"히트펌프 장치 목록 조회 실패: {e}")
            return []
    
    def get_all_groundpipe_devices(self) -> List[str]:
        """
        모든 지중배관 장치 ID 조회
        
        Returns:
            List[str]: 장치 ID 리스트 (예: ['GP_1', 'GP_2', ...])
        """
        try:
            query = """
                SELECT DISTINCT device_id
                FROM groundpipe
                ORDER BY device_id
            """
            result = execute_query(query, fetch_mode='all')
            return [row['device_id'] for row in result]
        except Exception as e:
            logger.error(f"지중배관 장치 목록 조회 실패: {e}")
            return []
    
    def get_all_power_devices(self) -> List[str]:
        """
        모든 전력량계 장치 ID 조회
        
        Returns:
            List[str]: 장치 ID 리스트 (예: ['Total', 'HP_1', ...])
        """
        try:
            query = """
                SELECT DISTINCT device_id
                FROM elec
                ORDER BY device_id
            """
            result = execute_query(query, fetch_mode='all')
            return [row['device_id'] for row in result]
        except Exception as e:
            logger.error(f"전력량계 장치 목록 조회 실패: {e}")
            return []
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 시계열 데이터 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_timeseries_heatpump(
        self,
        device_id: str,
        hours: int = 1,
        field: str = 't_in'
    ) -> List[Dict]:
        """
        히트펌프 시계열 데이터 조회
        
        Args:
            device_id: 장치 ID (예: 'HP_1')
            hours: 조회 시간 (시간 단위)
            field: 측정 항목 ('t_in', 't_out', 'flow', 'energy')
        
        Returns:
            List[Dict]: [{'timestamp': datetime, 'value': float}, ...]
        """
        try:
            # 필드명 매핑 (UI 필드명 → DB 컬럼명)
            field_mapping = {
                't_in': 'input_temp',
                't_out': 'output_temp',
                'flow': 'flow',
                'energy': 'energy'
            }
            
            db_field = field_mapping.get(field, field)
            start_time = datetime.now() - timedelta(hours=hours)
            
            query = f"""
                SELECT timestamp, {db_field}
                FROM heatpump
                WHERE device_id = %s
                  AND timestamp >= %s
                ORDER BY timestamp ASC
            """
            
            result = execute_query(query, (device_id, start_time), fetch_mode='all')
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row[db_field]) if row[db_field] is not None else 0.0
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"히트펌프 시계열 데이터 조회 실패: {e}")
            return []
    
    def get_timeseries_groundpipe(
        self,
        device_id: str,
        hours: int = 1,
        field: str = 't_in'
    ) -> List[Dict]:
        """
        지중배관 시계열 데이터 조회
        
        Args:
            device_id: 장치 ID (예: 'GP_1')
            hours: 조회 시간 (시간 단위)
            field: 측정 항목 ('t_in', 't_out', 'flow')
        
        Returns:
            List[Dict]: [{'timestamp': datetime, 'value': float}, ...]
        """
        try:
            # 필드명 매핑
            field_mapping = {
                't_in': 'input_temp',
                't_out': 'output_temp',
                'flow': 'flow'
            }
            
            db_field = field_mapping.get(field, field)
            start_time = datetime.now() - timedelta(hours=hours)
            
            query = f"""
                SELECT timestamp, {db_field}
                FROM groundpipe
                WHERE device_id = %s
                  AND timestamp >= %s
                ORDER BY timestamp ASC
            """
            
            result = execute_query(query, (device_id, start_time), fetch_mode='all')
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row[db_field]) if row[db_field] is not None else 0.0
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"지중배관 시계열 데이터 조회 실패: {e}")
            return []
    
    def get_timeseries_power(
        self,
        device_id: str,
        hours: int = 1,
        field: str = 'total_energy'
    ) -> List[Dict]:
        """
        전력량계 시계열 데이터 조회
        
        Args:
            device_id: 장치 ID (예: 'HP_1')
            hours: 조회 시간 (시간 단위)
            field: 측정 항목 ('total_energy')
        
        Returns:
            List[Dict]: [{'timestamp': datetime, 'value': float}, ...]
        """
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            query = """
                SELECT timestamp, total_energy
                FROM elec
                WHERE device_id = %s
                  AND timestamp >= %s
                ORDER BY timestamp ASC
            """
            
            result = execute_query(query, (device_id, start_time), fetch_mode='all')
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row['total_energy']) if row['total_energy'] is not None else 0.0
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"전력량계 시계열 데이터 조회 실패: {e}")
            return []
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 통계 데이터 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_statistics_heatpump(
        self,
        device_id: str,
        hours: int = 24,
        field: str = 't_in'
    ) -> Dict:
        """
        히트펌프 통계 데이터 조회
        
        Args:
            device_id: 장치 ID
            hours: 조회 시간 (시간 단위)
            field: 측정 항목
        
        Returns:
            Dict: {'latest': float, 'avg': float, 'max': float, 'min': float, 'count': int}
        """
        try:
            # 필드명 매핑
            field_mapping = {
                't_in': 'input_temp',
                't_out': 'output_temp',
                'flow': 'flow',
                'energy': 'energy'
            }
            
            db_field = field_mapping.get(field, field)
            start_time = datetime.now() - timedelta(hours=hours)
            
            # 최신 값
            query_latest = f"""
                SELECT {db_field}
                FROM heatpump
                WHERE device_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            latest_result = execute_query(query_latest, (device_id,), fetch_mode='one')
            latest = float(latest_result[db_field]) if latest_result and latest_result[db_field] is not None else 0.0
            
            # 통계 값
            query_stats = f"""
                SELECT 
                    AVG({db_field}) as avg,
                    MAX({db_field}) as max,
                    MIN({db_field}) as min,
                    COUNT(*) as count
                FROM heatpump
                WHERE device_id = %s
                  AND timestamp >= %s
            """
            stats_result = execute_query(query_stats, (device_id, start_time), fetch_mode='one')
            
            return {
                'latest': round(latest, 1),
                'avg': round(float(stats_result['avg']), 1) if stats_result['avg'] else 0.0,
                'max': round(float(stats_result['max']), 1) if stats_result['max'] else 0.0,
                'min': round(float(stats_result['min']), 1) if stats_result['min'] else 0.0,
                'count': int(stats_result['count'])
            }
        except Exception as e:
            logger.error(f"히트펌프 통계 데이터 조회 실패: {e}")
            return {'latest': 0.0, 'avg': 0.0, 'max': 0.0, 'min': 0.0, 'count': 0}
    
    def get_statistics_groundpipe(
        self,
        device_id: str,
        hours: int = 24,
        field: str = 't_in'
    ) -> Dict:
        """
        지중배관 통계 데이터 조회
        
        Args:
            device_id: 장치 ID
            hours: 조회 시간 (시간 단위)
            field: 측정 항목
        
        Returns:
            Dict: {'latest': float, 'avg': float, 'max': float, 'min': float, 'count': int}
        """
        try:
            # 필드명 매핑
            field_mapping = {
                't_in': 'input_temp',
                't_out': 'output_temp',
                'flow': 'flow'
            }
            
            db_field = field_mapping.get(field, field)
            start_time = datetime.now() - timedelta(hours=hours)
            
            # 최신 값
            query_latest = f"""
                SELECT {db_field}
                FROM groundpipe
                WHERE device_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            latest_result = execute_query(query_latest, (device_id,), fetch_mode='one')
            latest = float(latest_result[db_field]) if latest_result and latest_result[db_field] is not None else 0.0
            
            # 통계 값
            query_stats = f"""
                SELECT 
                    AVG({db_field}) as avg,
                    MAX({db_field}) as max,
                    MIN({db_field}) as min,
                    COUNT(*) as count
                FROM groundpipe
                WHERE device_id = %s
                  AND timestamp >= %s
            """
            stats_result = execute_query(query_stats, (device_id, start_time), fetch_mode='one')
            
            return {
                'latest': round(latest, 1),
                'avg': round(float(stats_result['avg']), 1) if stats_result['avg'] else 0.0,
                'max': round(float(stats_result['max']), 1) if stats_result['max'] else 0.0,
                'min': round(float(stats_result['min']), 1) if stats_result['min'] else 0.0,
                'count': int(stats_result['count'])
            }
        except Exception as e:
            logger.error(f"지중배관 통계 데이터 조회 실패: {e}")
            return {'latest': 0.0, 'avg': 0.0, 'max': 0.0, 'min': 0.0, 'count': 0}
    
    def get_statistics_power(
        self,
        device_id: str,
        hours: int = 24,
        field: str = 'total_energy'
    ) -> Dict:
        """
        전력량계 통계 데이터 조회
        
        Args:
            device_id: 장치 ID
            hours: 조회 시간 (시간 단위)
            field: 측정 항목 (항상 'total_energy')
        
        Returns:
            Dict: {'latest': float, 'avg': float, 'max': float, 'min': float, 'count': int}
        """
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            # 최신 값
            query_latest = """
                SELECT total_energy
                FROM elec
                WHERE device_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            latest_result = execute_query(query_latest, (device_id,), fetch_mode='one')
            latest = float(latest_result['total_energy']) if latest_result and latest_result['total_energy'] is not None else 0.0
            
            # 통계 값
            query_stats = """
                SELECT 
                    AVG(total_energy) as avg,
                    MAX(total_energy) as max,
                    MIN(total_energy) as min,
                    COUNT(*) as count
                FROM elec
                WHERE device_id = %s
                  AND timestamp >= %s
            """
            stats_result = execute_query(query_stats, (device_id, start_time), fetch_mode='one')
            
            return {
                'latest': round(latest, 1),
                'avg': round(float(stats_result['avg']), 1) if stats_result['avg'] else 0.0,
                'max': round(float(stats_result['max']), 1) if stats_result['max'] else 0.0,
                'min': round(float(stats_result['min']), 1) if stats_result['min'] else 0.0,
                'count': int(stats_result['count'])
            }
        except Exception as e:
            logger.error(f"전력량계 통계 데이터 조회 실패: {e}")
            return {'latest': 0.0, 'avg': 0.0, 'max': 0.0, 'min': 0.0, 'count': 0}


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="DEBUG")
    
    print("=" * 70)
    print("UI 데이터 서비스 테스트")
    print("=" * 70)
    
    # 데이터베이스 연결
    initialize_connection_pool()
    
    # 서비스 초기화
    service = UIDataService()
    
    # 1. 히트펌프 목록 조회
    print("\n[테스트 1] 히트펌프 장치 목록")
    devices = service.get_all_heatpump_devices()
    print(f"  장치: {devices}")
    
    # 2. 지중배관 목록 조회
    print("\n[테스트 2] 지중배관 장치 목록")
    devices = service.get_all_groundpipe_devices()
    print(f"  장치: {devices}")
    
    # 3. 전력량계 목록 조회
    print("\n[테스트 3] 전력량계 장치 목록")
    devices = service.get_all_power_devices()
    print(f"  장치: {devices}")
    
    # 4. 시계열 데이터 조회
    hp_devices = service.get_all_heatpump_devices()
    if hp_devices:
        device_id = hp_devices[0]
        print(f"\n[테스트 4] 시계열 데이터 조회 ({device_id})")
        data = service.get_timeseries_heatpump(device_id, hours=1)
        print(f"  데이터 개수: {len(data)}개")
        if data:
            print(f"  최신 데이터: {data[-1]}")
    
    # 5. 통계 데이터 조회
    if hp_devices:
        device_id = hp_devices[0]
        print(f"\n[테스트 5] 통계 데이터 조회 ({device_id})")
        stats = service.get_statistics_heatpump(device_id, hours=24)
        print(f"  통계: {stats}")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
