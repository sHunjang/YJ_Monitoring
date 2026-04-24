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
        # TTL 캐시 {cache_key: (expired_at, data)}
        self._cache: dict = {}
        self._cache_ttl = 55  # 초 (수집 주기 60초보다 살짝 짧게)

    def _cache_get(self, key: str):
        """캐시에서 값 조회. 만료됐으면 None 반환."""
        if key in self._cache:
            expired_at, data = self._cache[key]
            if datetime.now().timestamp() < expired_at:
                return data
            del self._cache[key]
        return None

    def _cache_set(self, key: str, data):
        """캐시에 값 저장."""
        expired_at = datetime.now().timestamp() + self._cache_ttl
        self._cache[key] = (expired_at, data)

    def _cache_invalidate(self, prefix: str = ''):
        """캐시 무효화 (특정 prefix 또는 전체)."""
        if prefix:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
        else:
            self._cache.clear()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 센서 목록 조회
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_all_heatpump_devices(self) -> List[str]:
        try:
            query = """
                SELECT DISTINCT device_id
                FROM heatpump
                ORDER BY device_id
            """
            result = execute_query(query, fetch_mode='all')
            devices = [row['device_id'] for row in result]

            # 숫자 기준 정렬 (HP_1, HP_2, HP_3, HP_4)
            devices.sort(key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 0)
            return devices
        except Exception as e:
            logger.error(f"히트펌프 장치 목록 조회 실패: {e}")
            return []
    
    def get_all_groundpipe_devices(self) -> List[str]:
        try:
            query = """
                SELECT DISTINCT device_id
                FROM groundpipe
                ORDER BY device_id
            """
            result = execute_query(query, fetch_mode='all')
            devices = [row['device_id'] for row in result]

            # 숫자 기준 정렬 (GP_1, GP_2, ... GP_10)
            devices.sort(key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 0)
            return devices
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
            
        cache_key = f'ts_hp_{device_id}_{hours}_{field}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        
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
            
            result = [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row[db_field]) if row[db_field] is not None else 0.0
                }
                for row in result
            ]
            
            self._cache_set(cache_key, result)
            
            return result

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
                
        cache_key = f'ts_gp_{device_id}_{hours}_{field}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        
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
            
            result = [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row[db_field]) if row[db_field] is not None else 0.0
                }
                for row in result
            ]
            self._cache_set(cache_key, result)
            
            return result
        
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
        
        cache_key = f'ts_elec_{device_id}_{hours}_{field}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        
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
            
            result = [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row['total_energy']) if row['total_energy'] is not None else 0.0
                }
                for row in result
            ]
            
            self._cache_set(cache_key, result)
            
            return result
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
    ) -> Dict:
        """
        히트펌프 통계 데이터 조회 (전체 필드 한 번에)

        Returns:
            Dict: {
                't_in':  {'latest', 'avg', 'max', 'min', 'count'},
                't_out': {'latest', 'avg', 'max', 'min', 'count'},
                'flow':  {'latest', 'avg', 'max', 'min', 'count'},
            }
        """
        
        cache_key = f'stats_hp_{device_id}_{hours}'
        cached = self._cache_get(cache_key)
        
        if cached is not None:
            return cached
        
        empty = {'latest': 0.0, 'avg': 0.0, 'max': 0.0, 'min': 0.0, 'count': 0}
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            query = """
                SELECT
                    -- 최신값 (DISTINCT ON 활용)
                    (SELECT input_temp  FROM heatpump WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1) AS latest_in,
                    (SELECT output_temp FROM heatpump WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1) AS latest_out,
                    (SELECT flow        FROM heatpump WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1) AS latest_flow,
                    -- 기간 통계
                    AVG(input_temp)   AS avg_in,  MAX(input_temp)   AS max_in,  MIN(input_temp)   AS min_in,
                    AVG(output_temp)  AS avg_out, MAX(output_temp)  AS max_out, MIN(output_temp)  AS min_out,
                    AVG(flow)         AS avg_flow, MAX(flow)         AS max_flow, MIN(flow)        AS min_flow,
                    COUNT(*)          AS cnt
                FROM heatpump
                WHERE device_id = %s
                AND timestamp >= %s
            """
            r = execute_query(
                query,
                (device_id, device_id, device_id, device_id, start_time),
                fetch_mode='one'
            )
            if not r:
                return {'t_in': empty, 't_out': empty, 'flow': empty}

            def _s(latest, avg, mx, mn, cnt):
                return {
                    'latest': round(float(latest), 1) if latest is not None else 0.0,
                    'avg':    round(float(avg),    1) if avg    is not None else 0.0,
                    'max':    round(float(mx),     1) if mx     is not None else 0.0,
                    'min':    round(float(mn),     1) if mn     is not None else 0.0,
                    'count':  int(cnt) if cnt is not None else 0,
                }

            result = {
                't_in':  _s(r['latest_in'],   r['avg_in'],   r['max_in'],   r['min_in'],   r['cnt']),
                't_out': _s(r['latest_out'],  r['avg_out'],  r['max_out'],  r['min_out'],  r['cnt']),
                'flow':  _s(r['latest_flow'], r['avg_flow'], r['max_flow'], r['min_flow'], r['cnt']),
            }
            
            self._cache_set(cache_key, result)
            
            return result

        except Exception as e:
            logger.error(f"히트펌프 통계 조회 실패: {e}")
            return {'t_in': empty, 't_out': empty, 'flow': empty}
    
    def get_statistics_groundpipe(
        self,
        device_id: str,
        hours: int = 24,
    ) -> Dict:
        
        cache_key = f'stats_gp_{device_id}_{hours}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        empty = {'latest': 0.0, 'avg': 0.0, 'max': 0.0, 'min': 0.0, 'count': 0}
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            query = """
                SELECT
                    (SELECT input_temp  FROM groundpipe WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1) AS latest_in,
                    (SELECT output_temp FROM groundpipe WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1) AS latest_out,
                    (SELECT flow        FROM groundpipe WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1) AS latest_flow,
                    AVG(input_temp)   AS avg_in,  MAX(input_temp)   AS max_in,  MIN(input_temp)   AS min_in,
                    AVG(output_temp)  AS avg_out, MAX(output_temp)  AS max_out, MIN(output_temp)  AS min_out,
                    AVG(flow)         AS avg_flow, MAX(flow)         AS max_flow, MIN(flow)        AS min_flow,
                    COUNT(*)          AS cnt
                FROM groundpipe
                WHERE device_id = %s
                AND timestamp >= %s
            """
            r = execute_query(
                query,
                (device_id, device_id, device_id, device_id, start_time),
                fetch_mode='one'
            )
            if not r:
                return {'t_in': empty, 't_out': empty, 'flow': empty}

            def _s(latest, avg, mx, mn, cnt):
                return {
                    'latest': round(float(latest), 1) if latest is not None else 0.0,
                    'avg':    round(float(avg),    1) if avg    is not None else 0.0,
                    'max':    round(float(mx),     1) if mx     is not None else 0.0,
                    'min':    round(float(mn),     1) if mn     is not None else 0.0,
                    'count':  int(cnt) if cnt is not None else 0,
                }

            result = {
                't_in':  _s(r['latest_in'],   r['avg_in'],   r['max_in'],   r['min_in'],   r['cnt']),
                't_out': _s(r['latest_out'],  r['avg_out'],  r['max_out'],  r['min_out'],  r['cnt']),
                'flow':  _s(r['latest_flow'], r['avg_flow'], r['max_flow'], r['min_flow'], r['cnt']),
            }
            
            self._cache_set(cache_key, result)
            
            return result 
        except Exception as e:
            logger.error(f"지중배관 통계 조회 실패: {e}")
            return {'t_in': empty, 't_out': empty, 'flow': empty}


    def get_statistics_power(self, device_id: str, hours: int = 24) -> Dict:
        
        cache_key = f'stats_pw_{device_id}_{hours}'
        cached = self._cache_get(cache_key)         
        if cached is not None:                      
            return cached                           
        
        empty = {'latest': 0.0, 'avg': 0.0, 'max': 0.0, 'min': 0.0, 'count': 0}
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            query = """
                SELECT
                    (SELECT total_energy FROM elec WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1) AS latest,
                    AVG(total_energy) AS avg,
                    MAX(total_energy) AS max,
                    MIN(total_energy) AS min,
                    COUNT(*)          AS cnt
                FROM elec
                WHERE device_id = %s
                AND timestamp >= %s
            """
            r = execute_query(query, (device_id, device_id, start_time), fetch_mode='one')
            if not r:
                return empty

            result = {
                'latest': round(float(r['latest']), 2) if r['latest'] is not None else 0.0,
                'avg':    round(float(r['avg']),    2) if r['avg']    is not None else 0.0,
                'max':    round(float(r['max']),    2) if r['max']    is not None else 0.0,
                'min':    round(float(r['min']),    2) if r['min']    is not None else 0.0,
                'count':  int(r['cnt']) if r['cnt'] is not None else 0,
            }
            self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"전력량계 통계 조회 실패: {e}")
            return empty


    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COP 계산용 범위 조회 (시작~끝 시각 지정)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_timeseries_heatpump_range(
        self,
        device_id: str,
        t_start: datetime,
        t_end: datetime,
        field: str = 't_in'
    ) -> List[Dict]:
        """
        히트펌프 특정 시간 범위 시계열 조회 (COP 슬롯 계산용)

        Args:
            device_id: 장치 ID
            t_start:   시작 시각 (포함)
            t_end:     종료 시각 (포함)
            field:     't_in' | 't_out' | 'flow'

        Returns:
            List[Dict]: [{'timestamp': datetime, 'value': float}, ...]
        """
        try:
            field_mapping = {
                't_in':  'input_temp',
                't_out': 'output_temp',
                'flow':  'flow',
            }
            db_field = field_mapping.get(field, field)

            query = f"""
                SELECT timestamp, {db_field}
                FROM heatpump
                WHERE device_id = %s
                  AND timestamp >= %s
                  AND timestamp <= %s
                ORDER BY timestamp ASC
            """
            result = execute_query(query, (device_id, t_start, t_end), fetch_mode='all')
            return [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row[db_field]) if row[db_field] is not None else None
                }
                for row in result
                if row[db_field] is not None   # NULL 행 제외 (센서 누락 대응)
            ]
        except Exception as e:
            logger.error(f"히트펌프 범위 조회 실패: {e}")
            return []

    def get_timeseries_power_range(
        self,
        device_id: str,
        t_start: datetime,
        t_end: datetime,
    ) -> List[Dict]:
        """
        전력량계 특정 시간 범위 시계열 조회 (COP 슬롯 계산용)

        Args:
            device_id: elec 테이블의 device_id (예: '히트펌프_1')
            t_start:   시작 시각 (포함)
            t_end:     종료 시각 (포함)

        Returns:
            List[Dict]: [{'timestamp': datetime, 'value': float}, ...]
              value = total_energy (누적값, 차분은 호출자에서 계산)
        """
        try:
            query = """
                SELECT timestamp, total_energy
                FROM elec
                WHERE device_id = %s
                  AND timestamp >= %s
                  AND timestamp <= %s
                ORDER BY timestamp ASC
            """
            result = execute_query(query, (device_id, t_start, t_end), fetch_mode='all')
            return [
                {
                    'timestamp': row['timestamp'],
                    'value': float(row['total_energy']) if row['total_energy'] is not None else None
                }
                for row in result
                if row['total_energy'] is not None
            ]
        except Exception as e:
            logger.error(f"전력량계 범위 조회 실패: {e}")
            return []


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