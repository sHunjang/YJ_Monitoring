# ==============================================
# 전력량계 데이터 모델
# ==============================================
"""
전력량계 데이터 모델

주요 클래스:
1. PowerMeterData: 전력량계 데이터
2. PowerMeterConfig: 전력량계 설정

사용 예:
    from sensors.power.models import PowerMeterData
    
    data = PowerMeterData(
        device_id='HP_1',
        total_energy=123.45
    )
    print(data.to_dict())
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class PowerMeterData:
    """
    전력량계 데이터
    
    누적 전력량 정보
    """
    device_id: str                          # 장치 ID (예: 'Total', 'HP_1', '열풍기_1')
    total_energy: Optional[float] = None    # 누적 전력량 (kWh)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_valid(self) -> bool:
        """
        데이터 유효성 확인
        
        Returns:
            bool: 전력량 값이 있으면 True
        """
        return self.total_energy is not None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'device_id': self.device_id,
            'total_energy': self.total_energy,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        return (
            f"PowerMeterData(device_id='{self.device_id}', "
            f"energy={self.total_energy}kWh)"
        )


@dataclass
class PowerMeterConfig:
    """
    전력량계 설정 정보
    
    config/power_meter_config.json에서 로드된 전력량계 정보
    """
    device_id: str
    name: str
    slave_id: int
    description: str = ""
    enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PowerMeterConfig':
        """
        딕셔너리에서 생성
        
        Args:
            data: 설정 딕셔너리
            
        Returns:
            PowerMeterConfig: 설정 인스턴스
        """
        return cls(
            device_id=data.get('device_id', ''),
            name=data.get('name', ''),
            slave_id=data.get('slave_id', 1),
            description=data.get('description', ''),
            enabled=data.get('enabled', True)
        )
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'device_id': self.device_id,
            'name': self.name,
            'slave_id': self.slave_id,
            'description': self.description,
            'enabled': self.enabled
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        return (
            f"PowerMeterConfig(device_id='{self.device_id}', "
            f"name='{self.name}', slave_id={self.slave_id})"
        )


@dataclass
class PowerMeterSystemConfig:
    """
    전력량계 시스템 설정
    
    전체 전력량계 시스템의 설정 정보
    """
    ip: str
    port: int = 502
    meters: List[PowerMeterConfig] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PowerMeterSystemConfig':
        """
        딕셔너리에서 생성
        
        Args:
            data: 설정 딕셔너리
            
        Returns:
            PowerMeterSystemConfig: 설정 인스턴스
        """
        meters = [
            PowerMeterConfig.from_dict(meter)
            for meter in data.get('meters', [])
        ]
        
        return cls(
            ip=data.get('ip', '192.168.1.200'),
            port=data.get('port', 502),
            meters=meters
        )
    
    def get_meter_config(self, device_id: str) -> Optional[PowerMeterConfig]:
        """
        특정 전력량계 설정 조회
        
        Args:
            device_id: 장치 ID
            
        Returns:
            PowerMeterConfig: 설정
            None: 찾을 수 없음
        """
        for meter in self.meters:
            if meter.device_id == device_id:
                return meter
        return None
    
    def get_enabled_meters(self) -> List[PowerMeterConfig]:
        """
        활성화된 전력량계 목록 조회
        
        Returns:
            list: 활성화된 전력량계 설정 목록
        """
        return [meter for meter in self.meters if meter.enabled]
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'ip': self.ip,
            'port': self.port,
            'meters': [meter.to_dict() for meter in self.meters]
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        return (
            f"PowerMeterSystemConfig(ip='{self.ip}', "
            f"port={self.port}, meters={len(self.meters)}개)"
        )


@dataclass
class EnergyStatistics:
    """
    전력량 통계
    
    일정 기간 동안의 전력량 통계 정보
    """
    device_id: str
    start_time: datetime
    end_time: datetime
    start_energy: Optional[float] = None    # 시작 전력량 (kWh)
    end_energy: Optional[float] = None      # 종료 전력량 (kWh)
    
    def get_consumed_energy(self) -> Optional[float]:
        """
        소비 전력량 계산
        
        Returns:
            float: 소비 전력량 (kWh)
            None: 계산 불가능
        """
        if self.start_energy is not None and self.end_energy is not None:
            consumed = self.end_energy - self.start_energy
            return round(consumed, 2) if consumed >= 0 else None
        return None
    
    def get_duration_hours(self) -> float:
        """
        기간 계산 (시간)
        
        Returns:
            float: 기간 (시간)
        """
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600
    
    def get_average_power(self) -> Optional[float]:
        """
        평균 전력 계산 (kW)
        
        Returns:
            float: 평균 전력 (kW)
            None: 계산 불가능
        """
        consumed = self.get_consumed_energy()
        duration = self.get_duration_hours()
        
        if consumed is not None and duration > 0:
            return round(consumed / duration, 2)
        return None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'device_id': self.device_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'start_energy': self.start_energy,
            'end_energy': self.end_energy,
            'consumed_energy': self.get_consumed_energy(),
            'duration_hours': self.get_duration_hours(),
            'average_power': self.get_average_power()
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        return (
            f"EnergyStatistics(device_id='{self.device_id}', "
            f"consumed={self.get_consumed_energy()}kWh, "
            f"avg_power={self.get_average_power()}kW)"
        )


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """데이터 모델 테스트"""
    print("=" * 70)
    print("전력량계 데이터 모델 테스트")
    print("=" * 70)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. PowerMeterData 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 1] PowerMeterData")
    
    meter_data = PowerMeterData(
        device_id='HP_1',
        total_energy=123.45
    )
    
    print(f"데이터: {meter_data}")
    print(f"유효성: {meter_data.is_valid()}")
    print(f"딕셔너리: {meter_data.to_dict()}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. PowerMeterConfig 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 2] PowerMeterConfig")
    
    config_dict = {
        'device_id': 'HP_1',
        'name': '히트펌프_1 전력량',
        'slave_id': 8,
        'description': '히트펌프 1호기 전력량계',
        'enabled': True
    }
    
    config = PowerMeterConfig.from_dict(config_dict)
    print(f"설정: {config}")
    print(f"딕셔너리: {config.to_dict()}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. PowerMeterSystemConfig 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 3] PowerMeterSystemConfig")
    
    system_dict = {
        'ip': '192.168.1.200',
        'port': 502,
        'meters': [
            {'device_id': 'Total', 'name': '전체', 'slave_id': 1},
            {'device_id': 'HP_1', 'name': '히트펌프_1', 'slave_id': 8}
        ]
    }
    
    system_config = PowerMeterSystemConfig.from_dict(system_dict)
    print(f"시스템 설정: {system_config}")
    print(f"전력량계 개수: {len(system_config.meters)}개")
    
    meter = system_config.get_meter_config('HP_1')
    print(f"HP_1 설정: {meter}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. EnergyStatistics 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 4] EnergyStatistics")
    
    from datetime import timedelta
    
    now = datetime.now()
    stats = EnergyStatistics(
        device_id='HP_1',
        start_time=now - timedelta(hours=1),
        end_time=now,
        start_energy=100.0,
        end_energy=110.5
    )
    
    print(f"통계: {stats}")
    print(f"소비 전력량: {stats.get_consumed_energy()} kWh")
    print(f"기간: {stats.get_duration_hours()} 시간")
    print(f"평균 전력: {stats.get_average_power()} kW")
    print(f"딕셔너리: {stats.to_dict()}")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
