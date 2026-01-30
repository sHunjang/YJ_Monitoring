# ==============================================
# 데이터베이스 연결 및 쿼리 모듈
# ==============================================
"""
PostgreSQL 데이터베이스 연결 및 CRUD 작업

주요 기능:
1. 데이터베이스 연결 풀 관리
2. 히트펌프 데이터 저장/조회
3. 지중배관 데이터 저장/조회
4. 전력량계 데이터 저장/조회
5. 트랜잭션 관리
6. UI 데이터 조회 (execute_query)

사용 예:
    from core.database import insert_heatpump_data
    
    insert_heatpump_data(
        device_id='HP_1',
        input_temp=25.5,
        output_temp=30.2,
        flow=15.3,
        energy=123.45
    )
"""

import logging
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from core.config import get_config

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 전역 연결 풀
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_connection_pool = None


def initialize_connection_pool(minconn: int = 1, maxconn: int = 10):
    """데이터베이스 연결 풀 초기화"""
    global _connection_pool
    
    if _connection_pool is not None:
        logger.warning("연결 풀이 이미 초기화되어 있습니다.")
        return
    
    try:
        config = get_config()
        
        logger.info("=" * 70)
        logger.info("데이터베이스 연결 풀 초기화")
        logger.info("=" * 70)
        logger.info(f"  Host: {config.db_host}:{config.db_port}")
        logger.info(f"  Database: {config.db_name}")
        logger.info(f"  연결 풀: {minconn}~{maxconn}개")
        
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=config.db_host,
            port=config.db_port,
            database=config.db_name,
            user=config.db_user,
            password=config.db_password
        )
        
        logger.info("✓ 데이터베이스 연결 풀 초기화 완료")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"✗ 데이터베이스 연결 풀 초기화 실패: {e}", exc_info=True)
        raise


def close_connection_pool():
    """연결 풀 종료"""
    global _connection_pool
    
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("✓ 데이터베이스 연결 풀 종료")


def get_connection():
    """연결 풀에서 연결 가져오기"""
    global _connection_pool
    
    if _connection_pool is None:
        initialize_connection_pool()
    
    return _connection_pool.getconn()


def return_connection(conn):
    """연결 풀에 연결 반환"""
    global _connection_pool
    
    if _connection_pool is not None:
        _connection_pool.putconn(conn)


@contextmanager
def get_db_connection():
    """데이터베이스 연결 Context Manager"""
    global _connection_pool
    
    if _connection_pool is None:
        initialize_connection_pool()
    
    conn = _connection_pool.getconn()
    
    try:
        yield conn
    finally:
        _connection_pool.putconn(conn)


def test_db_connection() -> bool:
    """데이터베이스 연결 테스트"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            
            if result[0] == 1:
                logger.info("✓ 데이터베이스 연결 테스트 성공")
                return True
            else:
                logger.error("✗ 데이터베이스 연결 테스트 실패")
                return False
                
    except Exception as e:
        logger.error(f"✗ 데이터베이스 연결 테스트 오류: {e}", exc_info=True)
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 쿼리 실행 헬퍼 함수 (UI용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def execute_query(query: str, params: tuple = None, fetch_mode: str = 'all'):
    """쿼리 실행 헬퍼 함수 (UI 데이터 조회용)"""
    connection = None
    cursor = None
    
    try:
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_mode == 'all':
            result = cursor.fetchall()
            return [dict(row) for row in result]
        elif fetch_mode == 'one':
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            connection.commit()
            return None
    
    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"쿼리 실행 실패: {e}")
        logger.error(f"쿼리: {query}")
        logger.error(f"파라미터: {params}")
        raise
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            return_connection(connection)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 히트펌프 데이터 저장/조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def insert_heatpump_data(
    device_id: str,
    input_temp: float,
    output_temp: float,
    flow: float,
    energy: float,
    timestamp: Optional[datetime] = None
) -> bool:
    """히트펌프 데이터 저장"""
    if timestamp is None:
        timestamp = datetime.now()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                INSERT INTO heatpump 
                (device_id, timestamp, input_temp, output_temp, flow, energy)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                device_id,
                timestamp,
                input_temp,
                output_temp,
                flow,
                energy
            ))
            
            conn.commit()
            cursor.close()
            
            logger.debug(
                f"[{device_id}] 히트펌프 데이터 저장: "
                f"input_temp={input_temp}°C, output_temp={output_temp}°C, "
                f"Flow={flow}L/min, Energy={energy}kWh"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"[{device_id}] 히트펌프 데이터 저장 실패: {e}", exc_info=True)
        return False


def get_heatpump_data(
    device_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """히트펌프 데이터 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, device_id, timestamp, 
                       input_temp, output_temp, flow, energy, created_at
                FROM heatpump
                WHERE device_id = %s
            """
            params = [device_id]
            
            if start_time:
                query += " AND timestamp >= %s"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= %s"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'device_id': row[1],
                    'timestamp': row[2],
                    'input_temp': float(row[3]) if row[3] else None,
                    'output_temp': float(row[4]) if row[4] else None,
                    'flow': float(row[5]) if row[5] else None,
                    'energy': float(row[6]) if row[6] else None,
                    'created_at': row[7]
                })
            
            return result
            
    except Exception as e:
        logger.error(f"[{device_id}] 히트펌프 데이터 조회 실패: {e}", exc_info=True)
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 지중배관 데이터 저장/조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def insert_groundpipe_data(
    device_id: str,
    input_temp: float,
    output_temp: float,
    flow: float,
    timestamp: Optional[datetime] = None
) -> bool:
    """지중배관 데이터 저장"""
    if timestamp is None:
        timestamp = datetime.now()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                INSERT INTO groundpipe 
                (device_id, timestamp, input_temp, output_temp, flow)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                device_id,
                timestamp,
                input_temp,
                output_temp,
                flow
            ))
            
            conn.commit()
            cursor.close()
            
            logger.debug(
                f"[{device_id}] 지중배관 데이터 저장: "
                f"input_temp={input_temp}°C, output_temp={output_temp}°C, Flow={flow}L/min"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"[{device_id}] 지중배관 데이터 저장 실패: {e}", exc_info=True)
        return False


def get_groundpipe_data(
    device_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """지중배관 데이터 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, device_id, timestamp, 
                       input_temp, output_temp, flow, created_at
                FROM groundpipe
                WHERE device_id = %s
            """
            params = [device_id]
            
            if start_time:
                query += " AND timestamp >= %s"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= %s"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'device_id': row[1],
                    'timestamp': row[2],
                    'input_temp': float(row[3]) if row[3] else None,
                    'output_temp': float(row[4]) if row[4] else None,
                    'flow': float(row[5]) if row[5] else None,
                    'created_at': row[6]
                })
            
            return result
            
    except Exception as e:
        logger.error(f"[{device_id}] 지중배관 데이터 조회 실패: {e}", exc_info=True)
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 전력량계 데이터 저장/조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def insert_power_meter_data(
    device_id: str,
    total_energy: float,
    timestamp: Optional[datetime] = None
) -> bool:
    """전력량계 데이터 저장"""
    if timestamp is None:
        timestamp = datetime.now()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                INSERT INTO elec 
                (device_id, timestamp, total_energy)
                VALUES (%s, %s, %s)
            """
            
            cursor.execute(query, (device_id, timestamp, total_energy))
            
            conn.commit()
            cursor.close()
            
            logger.debug(f"[{device_id}] 전력량계 데이터 저장: {total_energy}kWh")
            
            return True
            
    except Exception as e:
        logger.error(f"[{device_id}] 전력량계 데이터 저장 실패: {e}", exc_info=True)
        return False


def get_power_meter_data(
    device_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """전력량계 데이터 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, device_id, timestamp, total_energy, created_at
                FROM elec
                WHERE device_id = %s
            """
            params = [device_id]
            
            if start_time:
                query += " AND timestamp >= %s"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= %s"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'device_id': row[1],
                    'timestamp': row[2],
                    'total_energy': float(row[3]) if row[3] else None,
                    'created_at': row[4]
                })
            
            return result
            
    except Exception as e:
        logger.error(f"[{device_id}] 전력량계 데이터 조회 실패: {e}", exc_info=True)
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 유틸리티 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_all_heatpump_devices() -> List[str]:
    """모든 히트펌프 장치 ID 목록 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT DISTINCT device_id 
                FROM heatpump 
                ORDER BY device_id
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            
            return [row[0] for row in rows]
            
    except Exception as e:
        logger.error(f"히트펌프 장치 목록 조회 실패: {e}", exc_info=True)
        return []


def get_all_groundpipe_devices() -> List[str]:
    """모든 지중배관 장치 ID 목록 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT DISTINCT device_id 
                FROM groundpipe 
                ORDER BY device_id
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            
            return [row[0] for row in rows]
            
    except Exception as e:
        logger.error(f"지중배관 장치 목록 조회 실패: {e}", exc_info=True)
        return []


def get_all_power_meter_devices() -> List[str]:
    """모든 전력량계 장치 ID 목록 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT DISTINCT device_id 
                FROM elec 
                ORDER BY device_id
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            
            return [row[0] for row in rows]
            
    except Exception as e:
        logger.error(f"전력량계 장치 목록 조회 실패: {e}", exc_info=True)
        return []


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    from core.logging_config import setup_logging
    
    setup_logging(log_level="DEBUG")
    
    print("=" * 70)
    print("데이터베이스 모듈 테스트")
    print("=" * 70)
    
    print("\n[테스트 1] 데이터베이스 연결")
    if test_db_connection():
        print("✓ 연결 성공")
    else:
        print("✗ 연결 실패")
        exit(1)
    
    print("\n[테스트 2] 히트펌프 데이터 저장")
    success = insert_heatpump_data(
        device_id='HP_TEST',
        input_temp=25.5,
        output_temp=30.2,
        flow=15.3,
        energy=123.45
    )
    print(f"{'✓ 성공' if success else '✗ 실패'}")
    
    print("\n[테스트 3] 지중배관 데이터 저장")
    success = insert_groundpipe_data(
        device_id='UP_TEST',
        input_temp=20.1,
        output_temp=22.3,
        flow=10.5
    )
    print(f"{'✓ 성공' if success else '✗ 실패'}")
    
    print("\n[테스트 4] 전력량계 데이터 저장")
    success = insert_power_meter_data(
        device_id='TEST_METER',
        total_energy=999.99
    )
    print(f"{'✓ 성공' if success else '✗ 실패'}")
    
    print("\n[테스트 5] 히트펌프 데이터 조회")
    data = get_heatpump_data('HP_TEST', limit=5)
    print(f"조회된 레코드: {len(data)}개")
    if data:
        print(f"최신 데이터: {data[0]}")
    
    close_connection_pool()
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
