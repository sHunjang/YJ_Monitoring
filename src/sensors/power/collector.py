# ==============================================
# 전력량계 데이터 수집기
# ==============================================
"""
전력량계 데이터 수집 및 데이터베이스 저장

주요 기능:
1. PowerMeterReader를 통한 데이터 읽기
2. 데이터베이스 저장
3. 수집 통계 관리

사용 예:
    from sensors.power.collector import PowerMeterCollector
    
    collector = PowerMeterCollector()
    results = collector.collect_all()
    print(f"수집 성공: {results['success_count']}개")
"""

import logging
from datetime import datetime
from typing import Dict, Any

from sensors.power.reader import PowerMeterReader
from sensors.power.models import PowerMeterData
from core.database import insert_power_meter_batch

logger = logging.getLogger(__name__)


class PowerMeterCollector:

    def __init__(self, config_file: str = 'config/power_meter_config.json'):
        self.reader = PowerMeterReader(config_file)
        logger.info(
            f"PowerMeterReader 초기화: {self.reader.ip}:{self.reader.port}, "
            f"{len(self.reader.meter_configs)}개"
        )
        logger.info("PowerMeterCollector 초기화 완료")

    def collect_all(self) -> Dict[str, Any]:
        logger.info("=" * 70)
        logger.info("전력량계 데이터 수집 시작")
        logger.info("=" * 70)

        start_time = datetime.now()
        results = {
            'success_count': 0,
            'total_count': 0,
            'data': [],
            'errors': []
        }

        try:
            read_result = self.reader.read_all_meters()

            if isinstance(read_result, dict):
                data_list = []
                for device_id, data in read_result.items():
                    if isinstance(data, PowerMeterData):
                        data_list.append(data)
                    else:
                        logger.warning(f"[{device_id}] 잘못된 데이터 형식: {type(data)}")
            elif isinstance(read_result, list):
                data_list = read_result
            else:
                logger.error(f"예상치 못한 데이터 형식: {type(read_result)}")
                data_list = []

            results['total_count'] = len(data_list)

            # ── 배치 저장 + 원격 DB 전송 ──────────────
            batch = []
            for data in data_list:
                if not isinstance(data, PowerMeterData):
                    logger.warning(f"PowerMeterData 객체가 아님: {type(data)}")
                    continue
                batch.append({
                    'device_id':    data.device_id,
                    'total_energy': data.total_energy,
                    'timestamp':    data.timestamp,
                })
                results['data'].append(data)

            if batch:
                success = insert_power_meter_batch(batch)
                if success:
                    results['success_count'] = len(batch)
                    logger.debug(f"전력량계 배치 저장 완료: {len(batch)}건")
                else:
                    error_msg = "전력량계 배치 저장 실패"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)

            elapsed = (datetime.now() - start_time).total_seconds()

            logger.info("=" * 70)
            logger.info(
                f"전력량계 데이터 수집 완료: "
                f"{results['success_count']}/{results['total_count']}개 성공, "
                f"소요 시간: {elapsed:.2f}초"
            )
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"전력량계 데이터 수집 오류: {e}", exc_info=True)
            results['errors'].append(str(e))

        return results


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    from core.logging_config import setup_logging
    
    setup_logging(log_level="DEBUG")
    
    print("=" * 70)
    print("전력량계 수집기 테스트")
    print("=" * 70)
    
    collector = PowerMeterCollector()
    results = collector.collect_all()
    
    print(f"\n수집 결과:")
    print(f"  성공: {results['success_count']}/{results['total_count']}개")
    print(f"  오류: {len(results['errors'])}개")
    
    if results['data']:
        print(f"\n수집된 데이터:")
        for data in results['data']:
            print(f"  - {data}")
    
    if results['errors']:
        print(f"\n오류 목록:")
        for error in results['errors']:
            print(f"  - {error}")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
