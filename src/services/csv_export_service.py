# ==============================================
# CSV 내보내기 서비스
# ==============================================
"""
데이터베이스 데이터를 CSV 파일로 내보내기

기능:
- 히트펌프 데이터 내보내기
- 지중배관 데이터 내보내기
- 전력량계 데이터 내보내기
- 날짜 범위 지정
- 장치별 파일 생성
"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from core.database import execute_query

logger = logging.getLogger(__name__)


class CSVExportService:
    """CSV 내보내기 서비스"""
    
    def __init__(self):
        """초기화"""
        logger.info("CSVExportService 초기화")
    
    def export_heatpump_data(
        self,
        output_dir: str,
        device_ids: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        single_file: bool = False
    ) -> dict:
        """
        히트펌프 데이터 CSV 내보내기
        
        Args:
            output_dir: 출력 디렉토리
            device_ids: 장치 ID 리스트 (None이면 전체)
            start_date: 시작 날짜 (None이면 전체)
            end_date: 종료 날짜 (None이면 전체)
            single_file: True면 하나의 파일로, False면 장치별 파일로
        
        Returns:
            dict: {'success': bool, 'files': List[str], 'total_rows': int}
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 장치 목록 조회
            if device_ids is None:
                query = "SELECT DISTINCT device_id FROM heatpump ORDER BY device_id"
                result = execute_query(query, fetch_mode='all')
                device_ids = [row['device_id'] for row in result]
            
            if not device_ids:
                logger.warning("내보낼 히트펌프 장치가 없습니다.")
                return {'success': False, 'files': [], 'total_rows': 0}
            
            exported_files = []
            total_rows = 0
            
            if single_file:
                # 하나의 파일로 내보내기
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'heatpump_all_{timestamp}.csv'
                filepath = output_path / filename
                
                rows = self._export_heatpump_single_file(
                    filepath, device_ids, start_date, end_date
                )
                
                if rows > 0:
                    exported_files.append(str(filepath))
                    total_rows += rows
            else:
                # 장치별 파일로 내보내기
                for device_id in device_ids:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'heatpump_{device_id}_{timestamp}.csv'
                    filepath = output_path / filename
                    
                    rows = self._export_heatpump_device_file(
                        filepath, device_id, start_date, end_date
                    )
                    
                    if rows > 0:
                        exported_files.append(str(filepath))
                        total_rows += rows
            
            logger.info(f"히트펌프 데이터 내보내기 완료: {len(exported_files)}개 파일, {total_rows}행")
            
            return {
                'success': True,
                'files': exported_files,
                'total_rows': total_rows
            }
        
        except Exception as e:
            logger.error(f"히트펌프 데이터 내보내기 실패: {e}", exc_info=True)
            return {'success': False, 'files': [], 'total_rows': 0}
    
    def _export_heatpump_single_file(
        self,
        filepath: Path,
        device_ids: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> int:
        """히트펌프 데이터를 하나의 파일로 내보내기"""
        query = """
            SELECT 
                device_id,
                timestamp,
                input_temp,
                output_temp,
                flow,
                energy
            FROM heatpump
            WHERE device_id = ANY(%s)
        """
        params = [device_ids]
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY device_id, timestamp ASC"
        
        data = execute_query(query, tuple(params), fetch_mode='all')
        
        if not data:
            return 0
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                '장치ID',
                '측정시간',
                '입구온도(°C)',
                '출구온도(°C)',
                '유량(L/min)',
                '누적전력량(kWh)'
            ])
            
            # 데이터
            for row in data:
                writer.writerow([
                    row['device_id'],
                    row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else '',
                    f"{row['input_temp']:.2f}" if row['input_temp'] is not None else '',
                    f"{row['output_temp']:.2f}" if row['output_temp'] is not None else '',
                    f"{row['flow']:.2f}" if row['flow'] is not None else '',
                    f"{row['energy']:.2f}" if row['energy'] is not None else ''
                ])
        
        return len(data)
    
    def _export_heatpump_device_file(
        self,
        filepath: Path,
        device_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> int:
        """히트펌프 데이터를 장치별 파일로 내보내기"""
        query = """
            SELECT 
                timestamp,
                input_temp,
                output_temp,
                flow,
                energy
            FROM heatpump
            WHERE device_id = %s
        """
        params = [device_id]
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY timestamp ASC"
        
        data = execute_query(query, tuple(params), fetch_mode='all')
        
        if not data:
            return 0
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                '측정시간',
                '입구온도(°C)',
                '출구온도(°C)',
                '유량(L/min)',
                '누적전력량(kWh)'
            ])
            
            # 데이터
            for row in data:
                writer.writerow([
                    row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else '',
                    f"{row['input_temp']:.2f}" if row['input_temp'] is not None else '',
                    f"{row['output_temp']:.2f}" if row['output_temp'] is not None else '',
                    f"{row['flow']:.2f}" if row['flow'] is not None else '',
                    f"{row['energy']:.2f}" if row['energy'] is not None else ''
                ])
        
        return len(data)
    
    def export_groundpipe_data(
        self,
        output_dir: str,
        device_ids: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        single_file: bool = False
    ) -> dict:
        """
        지중배관 데이터 CSV 내보내기
        
        Args:
            output_dir: 출력 디렉토리
            device_ids: 장치 ID 리스트 (None이면 전체)
            start_date: 시작 날짜 (None이면 전체)
            end_date: 종료 날짜 (None이면 전체)
            single_file: True면 하나의 파일로, False면 장치별 파일로
        
        Returns:
            dict: {'success': bool, 'files': List[str], 'total_rows': int}
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 장치 목록 조회
            if device_ids is None:
                query = "SELECT DISTINCT device_id FROM groundpipe ORDER BY device_id"
                result = execute_query(query, fetch_mode='all')
                device_ids = [row['device_id'] for row in result]
            
            if not device_ids:
                logger.warning("내보낼 지중배관 장치가 없습니다.")
                return {'success': False, 'files': [], 'total_rows': 0}
            
            exported_files = []
            total_rows = 0
            
            if single_file:
                # 하나의 파일로 내보내기
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'groundpipe_all_{timestamp}.csv'
                filepath = output_path / filename
                
                rows = self._export_groundpipe_single_file(
                    filepath, device_ids, start_date, end_date
                )
                
                if rows > 0:
                    exported_files.append(str(filepath))
                    total_rows += rows
            else:
                # 장치별 파일로 내보내기
                for device_id in device_ids:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'groundpipe_{device_id}_{timestamp}.csv'
                    filepath = output_path / filename
                    
                    rows = self._export_groundpipe_device_file(
                        filepath, device_id, start_date, end_date
                    )
                    
                    if rows > 0:
                        exported_files.append(str(filepath))
                        total_rows += rows
            
            logger.info(f"지중배관 데이터 내보내기 완료: {len(exported_files)}개 파일, {total_rows}행")
            
            return {
                'success': True,
                'files': exported_files,
                'total_rows': total_rows
            }
        
        except Exception as e:
            logger.error(f"지중배관 데이터 내보내기 실패: {e}", exc_info=True)
            return {'success': False, 'files': [], 'total_rows': 0}
    
    def _export_groundpipe_single_file(
        self,
        filepath: Path,
        device_ids: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> int:
        """지중배관 데이터를 하나의 파일로 내보내기"""
        query = """
            SELECT 
                device_id,
                timestamp,
                input_temp,
                output_temp,
                flow
            FROM groundpipe
            WHERE device_id = ANY(%s)
        """
        params = [device_ids]
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY device_id, timestamp ASC"
        
        data = execute_query(query, tuple(params), fetch_mode='all')
        
        if not data:
            return 0
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                '장치ID',
                '측정시간',
                '입구온도(°C)',
                '출구온도(°C)',
                '유량(L/min)'
            ])
            
            # 데이터
            for row in data:
                writer.writerow([
                    row['device_id'],
                    row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else '',
                    f"{row['input_temp']:.2f}" if row['input_temp'] is not None else '',
                    f"{row['output_temp']:.2f}" if row['output_temp'] is not None else '',
                    f"{row['flow']:.2f}" if row['flow'] is not None else ''
                ])
        
        return len(data)
    
    def _export_groundpipe_device_file(
        self,
        filepath: Path,
        device_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> int:
        """지중배관 데이터를 장치별 파일로 내보내기"""
        query = """
            SELECT 
                timestamp,
                input_temp,
                output_temp,
                flow
            FROM groundpipe
            WHERE device_id = %s
        """
        params = [device_id]
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY timestamp ASC"
        
        data = execute_query(query, tuple(params), fetch_mode='all')
        
        if not data:
            return 0
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                '측정시간',
                '입구온도(°C)',
                '출구온도(°C)',
                '유량(L/min)'
            ])
            
            # 데이터
            for row in data:
                writer.writerow([
                    row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else '',
                    f"{row['input_temp']:.2f}" if row['input_temp'] is not None else '',
                    f"{row['output_temp']:.2f}" if row['output_temp'] is not None else '',
                    f"{row['flow']:.2f}" if row['flow'] is not None else ''
                ])
        
        return len(data)
    
    def export_power_meter_data(
        self,
        output_dir: str,
        device_ids: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        single_file: bool = False
    ) -> dict:
        """
        전력량계 데이터 CSV 내보내기
        
        Args:
            output_dir: 출력 디렉토리
            device_ids: 장치 ID 리스트 (None이면 전체)
            start_date: 시작 날짜 (None이면 전체)
            end_date: 종료 날짜 (None이면 전체)
            single_file: True면 하나의 파일로, False면 장치별 파일로
        
        Returns:
            dict: {'success': bool, 'files': List[str], 'total_rows': int}
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 장치 목록 조회
            if device_ids is None:
                query = "SELECT DISTINCT device_id FROM elec ORDER BY device_id"
                result = execute_query(query, fetch_mode='all')
                device_ids = [row['device_id'] for row in result]
            
            if not device_ids:
                logger.warning("내보낼 전력량계 장치가 없습니다.")
                return {'success': False, 'files': [], 'total_rows': 0}
            
            exported_files = []
            total_rows = 0
            
            if single_file:
                # 하나의 파일로 내보내기
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'power_all_{timestamp}.csv'
                filepath = output_path / filename
                
                rows = self._export_power_single_file(
                    filepath, device_ids, start_date, end_date
                )
                
                if rows > 0:
                    exported_files.append(str(filepath))
                    total_rows += rows
            else:
                # 장치별 파일로 내보내기
                for device_id in device_ids:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'power_{device_id}_{timestamp}.csv'
                    filepath = output_path / filename
                    
                    rows = self._export_power_device_file(
                        filepath, device_id, start_date, end_date
                    )
                    
                    if rows > 0:
                        exported_files.append(str(filepath))
                        total_rows += rows
            
            logger.info(f"전력량계 데이터 내보내기 완료: {len(exported_files)}개 파일, {total_rows}행")
            
            return {
                'success': True,
                'files': exported_files,
                'total_rows': total_rows
            }
        
        except Exception as e:
            logger.error(f"전력량계 데이터 내보내기 실패: {e}", exc_info=True)
            return {'success': False, 'files': [], 'total_rows': 0}
    
    def _export_power_single_file(
        self,
        filepath: Path,
        device_ids: List[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> int:
        """전력량계 데이터를 하나의 파일로 내보내기"""
        query = """
            SELECT 
                device_id,
                timestamp,
                total_energy
            FROM elec
            WHERE device_id = ANY(%s)
        """
        params = [device_ids]
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY device_id, timestamp ASC"
        
        data = execute_query(query, tuple(params), fetch_mode='all')
        
        if not data:
            return 0
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                '장치ID',
                '측정시간',
                '누적전력량(kWh)'
            ])
            
            # 데이터
            for row in data:
                writer.writerow([
                    row['device_id'],
                    row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else '',
                    f"{row['total_energy']:.2f}" if row['total_energy'] is not None else ''
                ])
        
        return len(data)
    
    def _export_power_device_file(
        self,
        filepath: Path,
        device_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> int:
        """전력량계 데이터를 장치별 파일로 내보내기"""
        query = """
            SELECT 
                timestamp,
                total_energy
            FROM elec
            WHERE device_id = %s
        """
        params = [device_id]
        
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY timestamp ASC"
        
        data = execute_query(query, tuple(params), fetch_mode='all')
        
        if not data:
            return 0
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                '측정시간',
                '누적전력량(kWh)'
            ])
            
            # 데이터
            for row in data:
                writer.writerow([
                    row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else '',
                    f"{row['total_energy']:.2f}" if row['total_energy'] is not None else ''
                ])
        
        return len(data)


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="DEBUG")
    initialize_connection_pool()
    
    print("=" * 70)
    print("CSV 내보내기 서비스 테스트")
    print("=" * 70)
    
    service = CSVExportService()
    
    # 테스트: 전체 데이터 장치별로 내보내기
    print("\n[테스트 1] 히트펌프 데이터 내보내기 (장치별)")
    result = service.export_heatpump_data(
        output_dir='exports',
        single_file=False
    )
    print(f"  성공: {result['success']}")
    print(f"  파일: {len(result['files'])}개")
    print(f"  총 행: {result['total_rows']}행")
    
    print("\n[테스트 2] 전력량계 데이터 내보내기 (하나의 파일)")
    result = service.export_power_meter_data(
        output_dir='exports',
        single_file=True
    )
    print(f"  성공: {result['success']}")
    print(f"  파일: {len(result['files'])}개")
    print(f"  총 행: {result['total_rows']}행")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
