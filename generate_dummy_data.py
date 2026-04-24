# ==============================================
# 더미 데이터 생성 스크립트
# ==============================================
"""
테스트용 더미 데이터를 DB에 삽입합니다.

동작:
- 히트펌프 4개 / 지중배관 10개 / 전력량계 11개
- 최근 24시간치 데이터를 10초 간격으로 생성
- 실제 현장과 유사한 값 범위 사용

실행:
    python generate_dummy_data.py           # 24시간치
    python generate_dummy_data.py --hours 1 # 1시간치
    python generate_dummy_data.py --clear   # 기존 더미 데이터 삭제
"""

import sys
import math
import random
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 경로 추가
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / 'src'))

from src.core.logging_config import setup_logging
from src.core.database import initialize_connection_pool, get_db_connection

setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 장치 목록
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HP_DEVICES = ['HP_1', 'HP_2', 'HP_3', 'HP_4']
GP_DEVICES = ['GP_1', 'GP_2', 'GP_3', 'GP_4', 'GP_5',
              'GP_6', 'GP_7', 'GP_8', 'GP_9', 'GP_10']
PM_DEVICES = ['Total', '열풍기_1', '열풍기_2', '열풍기_3',
              '열풍기_4', '열풍기_5', '열풍기_6',
              '히트펌프_1', '히트펌프_2', '히트펌프_3', '히트펌프_4']

INTERVAL_SECONDS = 10  # 데이터 간격


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 값 생성 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def sine_wave(t: float, base: float, amp: float, period: float = 3600) -> float:
    """시간에 따라 자연스럽게 변하는 사인파 값"""
    return base + amp * math.sin(2 * math.pi * t / period)


def generate_hp_data(device_id: str, timestamp: datetime, idx: int) -> dict:
    """히트펌프 데이터 생성"""
    t = timestamp.timestamp()
    # 장치마다 위상 다르게
    phase = HP_DEVICES.index(device_id) * 900

    t_in  = round(sine_wave(t + phase, 25.0, 8.0, 7200) + random.uniform(-0.5, 0.5), 1)
    t_out = round(t_in + random.uniform(3.0, 7.0), 1)
    flow  = int(sine_wave(t + phase, 150, 50, 3600) + random.uniform(-5, 5))
    flow  = max(0, flow)

    return {
        'device_id':   device_id,
        'input_temp':  t_in,
        'output_temp': t_out,
        'flow':        flow,
        'energy':      None,
        'timestamp':   timestamp,
    }


def generate_gp_data(device_id: str, timestamp: datetime, idx: int) -> dict:
    """지중배관 데이터 생성"""
    t = timestamp.timestamp()
    phase = GP_DEVICES.index(device_id) * 600

    t_in  = round(sine_wave(t + phase, 18.0, 5.0, 10800) + random.uniform(-0.3, 0.3), 1)
    t_out = round(t_in + random.uniform(1.5, 4.0), 1)
    flow  = int(sine_wave(t + phase, 120, 40, 3600) + random.uniform(-5, 5))
    flow  = max(0, flow)

    return {
        'device_id':   device_id,
        'input_temp':  t_in,
        'output_temp': t_out,
        'flow':        flow,
        'timestamp':   timestamp,
    }


def generate_pm_data(device_id: str, timestamp: datetime, idx: int,
                     base_energy: dict) -> dict:
    """전력량계 데이터 생성 (누적값)"""
    # 10초마다 조금씩 증가 (누적 전력량)
    if device_id == 'Total':
        increment = random.uniform(0.05, 0.15)
    elif '열풍기' in device_id:
        increment = random.uniform(0.01, 0.05)
    else:
        increment = random.uniform(0.005, 0.02)

    base_energy[device_id] = base_energy.get(device_id, 0.0) + increment

    return {
        'device_id':    device_id,
        'total_energy': round(base_energy[device_id], 2),
        'timestamp':    timestamp,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB 삽입
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def insert_batch(conn, table: str, columns: list, rows: list):
    """배치 INSERT"""
    if not rows:
        return
    placeholders = ', '.join(['%s'] * len(columns))
    col_names    = ', '.join(columns)
    query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.executemany(query, rows)
    conn.commit()
    cursor.close()


def clear_dummy_data():
    """기존 데이터 전체 삭제 (테스트용)"""
    print("\n⚠️  기존 데이터를 삭제합니다...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM heatpump")
        cursor.execute("DELETE FROM groundpipe")
        cursor.execute("DELETE FROM elec")
        conn.commit()
        cursor.close()
    print("✓ 기존 데이터 삭제 완료")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    parser = argparse.ArgumentParser(description='더미 데이터 생성')
    parser.add_argument('--hours', type=int, default=24,
                        help='생성할 시간 범위 (기본: 24시간)')
    parser.add_argument('--clear', action='store_true',
                        help='기존 데이터 삭제 후 생성')
    args = parser.parse_args()

    print("=" * 60)
    print("여주 센서 모니터링 — 더미 데이터 생성")
    print("=" * 60)

    # DB 연결
    initialize_connection_pool()

    if args.clear:
        clear_dummy_data()

    # 타임스탬프 목록 생성
    now        = datetime.now()
    start_time = now - timedelta(hours=args.hours)
    total_seconds = int(args.hours * 3600)
    steps     = total_seconds // INTERVAL_SECONDS

    print(f"\n생성 범위: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {now.strftime('%H:%M:%S')}")
    print(f"데이터 간격: {INTERVAL_SECONDS}초")
    print(f"총 타임스탬프: {steps:,}개")
    print(f"히트펌프 {len(HP_DEVICES)}대 × {steps:,}건 = {len(HP_DEVICES)*steps:,}건")
    print(f"지중배관 {len(GP_DEVICES)}대 × {steps:,}건 = {len(GP_DEVICES)*steps:,}건")
    print(f"전력량계 {len(PM_DEVICES)}대 × {steps:,}건 = {len(PM_DEVICES)*steps:,}건")
    total = (len(HP_DEVICES) + len(GP_DEVICES) + len(PM_DEVICES)) * steps
    print(f"총 {total:,}건 삽입 예정\n")

    base_energy = {}  # 전력량계 누적값 추적

    hp_batch = []
    gp_batch = []
    pm_batch = []

    BATCH_SIZE = 1000  # 1000건마다 DB에 삽입

    inserted_hp = inserted_gp = inserted_pm = 0

    with get_db_connection() as conn:
        for idx in range(steps):
            ts = start_time + timedelta(seconds=idx * INTERVAL_SECONDS)

            # 히트펌프
            for dev in HP_DEVICES:
                d = generate_hp_data(dev, ts, idx)
                hp_batch.append((
                    d['device_id'], d['timestamp'],
                    d['input_temp'], d['output_temp'],
                    d['flow'], d['energy']
                ))

            # 지중배관
            for dev in GP_DEVICES:
                d = generate_gp_data(dev, ts, idx)
                gp_batch.append((
                    d['device_id'], d['timestamp'],
                    d['input_temp'], d['output_temp'],
                    d['flow']
                ))

            # 전력량계
            for dev in PM_DEVICES:
                d = generate_pm_data(dev, ts, idx, base_energy)
                pm_batch.append((
                    d['device_id'], d['timestamp'], d['total_energy']
                ))

            # 배치 삽입
            if len(hp_batch) >= BATCH_SIZE * len(HP_DEVICES):
                insert_batch(conn, 'heatpump',
                    ['device_id', 'timestamp', 'input_temp', 'output_temp', 'flow', 'energy'],
                    hp_batch)
                inserted_hp += len(hp_batch)
                hp_batch = []
                print(f"  히트펌프 {inserted_hp:,}건 삽입 완료...")

            if len(gp_batch) >= BATCH_SIZE * len(GP_DEVICES):
                insert_batch(conn, 'groundpipe',
                    ['device_id', 'timestamp', 'input_temp', 'output_temp', 'flow'],
                    gp_batch)
                inserted_gp += len(gp_batch)
                gp_batch = []
                print(f"  지중배관 {inserted_gp:,}건 삽입 완료...")

            if len(pm_batch) >= BATCH_SIZE * len(PM_DEVICES):
                insert_batch(conn, 'elec',
                    ['device_id', 'timestamp', 'total_energy'],
                    pm_batch)
                inserted_pm += len(pm_batch)
                pm_batch = []
                print(f"  전력량계 {inserted_pm:,}건 삽입 완료...")

        # 나머지 삽입
        if hp_batch:
            insert_batch(conn, 'heatpump',
                ['device_id', 'timestamp', 'input_temp', 'output_temp', 'flow', 'energy'],
                hp_batch)
            inserted_hp += len(hp_batch)

        if gp_batch:
            insert_batch(conn, 'groundpipe',
                ['device_id', 'timestamp', 'input_temp', 'output_temp', 'flow'],
                gp_batch)
            inserted_gp += len(gp_batch)

        if pm_batch:
            insert_batch(conn, 'elec',
                ['device_id', 'timestamp', 'total_energy'],
                pm_batch)
            inserted_pm += len(pm_batch)

    print("\n" + "=" * 60)
    print("✓ 더미 데이터 생성 완료")
    print(f"  히트펌프:  {inserted_hp:,}건")
    print(f"  지중배관:  {inserted_gp:,}건")
    print(f"  전력량계:  {inserted_pm:,}건")
    print(f"  합계:      {inserted_hp + inserted_gp + inserted_pm:,}건")
    print("=" * 60)


if __name__ == '__main__':
    main()