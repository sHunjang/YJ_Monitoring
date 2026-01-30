# ==============================================
# 플라스틱 함 센서 데이터 모델
# ==============================================
"""
플라스틱 함 센서 데이터 모델

주요 클래스:
1. BoxSensorData: 센서 데이터 (온도 2개 + 유량)
2. HeatpumpData: 히트펌프 데이터 (센서 + 전력량)
3. GroundpipeData: 지중배관 데이터 (센서만)

사용 예:
    from sensors.box.models import HeatpumpData
    
    data = HeatpumpData(
        device_id='HP_1',
        input_temp=25.5,
        output_temp=30.2,
        flow=15.3,
        energy=123.45
    )
    print(data.to_dict())
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BoxSensorData:
    """
    플라스틱 함 센서 데이터 (기본)
    
    온도센서 2개 + 유량센서 1개
    """
    device_id: str
    input_temp: Optional[float] = None      # 입구 온도 (°C)
    output_temp: Optional[float] = None     # 출구 온도 (°C)
    flow: Optional[float] = None            # 유량 (L/min)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_valid(self) -> bool:
        """
        데이터 유효성 확인
        
        Returns:
            bool: 최소 하나의 센서 값이 있으면 True
        """
        return any([
            self.input_temp is not None,
            self.output_temp is not None,
            self.flow is not None
        ])
    
    def get_temp_diff(self) -> Optional[float]:
        """
        온도 차이 계산 (출구 - 입구)
        
        Returns:
            float: 온도 차이 (°C)
            None: 계산 불가능
        """
        if self.input_temp is not None and self.output_temp is not None:
            return round(self.output_temp - self.input_temp, 2)
        return None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'device_id': self.device_id,
            'input_temp': self.input_temp,
            'output_temp': self.output_temp,
            'flow': self.flow,
            'timestamp': self.timestamp.isoformat(),
            'temp_diff': self.get_temp_diff()
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        return (
            f"BoxSensorData(device_id='{self.device_id}', "
            f"T_in={self.input_temp}°C, T_out={self.output_temp}°C, "
            f"flow={self.flow}L/min)"
        )


@dataclass
class HeatpumpData(BoxSensorData):
    """
    히트펌프 데이터
    
    센서 데이터 + 전력량
    """
    energy: Optional[float] = None          # 누적 전력량 (kWh)
    
    def calculate_cop(self) -> Optional[float]:
        """
        COP (성능계수) 계산
        
        COP = (유량 × 온도차이 × 비열 × 밀도) / (전력 × 3600)
        
        참고:
        - 물의 비열: 4.186 kJ/(kg·°C)
        - 물의 밀도: 1 kg/L
        
        Returns:
            float: COP 값
            None: 계산 불가능
        """
        if (self.flow is not None and 
            self.input_temp is not None and 
            self.output_temp is not None and
            self.energy is not None and
            self.energy > 0):
            
            temp_diff = self.output_temp - self.input_temp
            
            if abs(temp_diff) < 0.1:  # 온도 차이가 너무 작음
                return None
            
            # 열량 계산 (kW)
            # Q = 유량(L/min) × 온도차(°C) × 비열(4.186) × 밀도(1) / 60
            heat_output = (self.flow * temp_diff * 4.186) / 60
            
            # COP 계산 (순간값 개념)
            # 실제로는 전력량이 누적값이므로 정확한 계산 어려움
            # 여기서는 간단히 계산
            cop = abs(heat_output / self.energy) if self.energy > 0 else None
            
            return round(cop, 2) if cop else None
        
        return None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        base_dict = super().to_dict()
        base_dict.update({
            'energy': self.energy,
            'cop': self.calculate_cop()
        })
        return base_dict
    
    def __str__(self) -> str:
        """문자열 표현"""
        return (
            f"HeatpumpData(device_id='{self.device_id}', "
            f"T_in={self.input_temp}°C, T_out={self.output_temp}°C, "
            f"flow={self.flow}L/min, energy={self.energy}kWh)"
        )


@dataclass
class GroundpipeData(BoxSensorData):
    """
    지중배관 데이터
    
    센서 데이터만 (전력량 없음)
    """
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return super().to_dict()
    
    def __str__(self) -> str:
        """문자열 표현"""
        return (
            f"GroundpipeData(device_id='{self.device_id}', "
            f"T_in={self.input_temp}°C, T_out={self.output_temp}°C, "
            f"flow={self.flow}L/min)"
        )


@dataclass
class DeviceConfig:
    """
    장치 설정 정보
    
    config/box_ips.json에서 로드된 장치 정보
    """
    device_id: str
    name: str
    ip: str
    port: int = 502
    description: str = ""
    enabled: bool = True
    temp1_slave_id: int = 1
    temp2_slave_id: int = 2
    flow_slave_id: int = 3
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DeviceConfig':
        """
        딕셔너리에서 생성
        
        Args:
            data: 설정 딕셔너리
            
        Returns:
            DeviceConfig: 설정 인스턴스
        """
        sensors = data.get('sensors', {})
        
        return cls(
            device_id=data.get('device_id', ''),
            name=data.get('name', ''),
            ip=data.get('ip', ''),
            port=data.get('port', 502),
            description=data.get('description', ''),
            enabled=data.get('enabled', True),
            temp1_slave_id=sensors.get('temp1_slave_id', 1),
            temp2_slave_id=sensors.get('temp2_slave_id', 2),
            flow_slave_id=sensors.get('flow_slave_id', 3)
        )
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'device_id': self.device_id,
            'name': self.name,
            'ip': self.ip,
            'port': self.port,
            'description': self.description,
            'enabled': self.enabled,
            'sensors': {
                'temp1_slave_id': self.temp1_slave_id,
                'temp2_slave_id': self.temp2_slave_id,
                'flow_slave_id': self.flow_slave_id
            }
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"DeviceConfig(device_id='{self.device_id}', name='{self.name}', ip='{self.ip}')"


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    """데이터 모델 테스트"""
    print("=" * 70)
    print("플라스틱 함 센서 데이터 모델 테스트")
    print("=" * 70)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. BoxSensorData 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 1] BoxSensorData")
    
    sensor_data = BoxSensorData(
        device_id='TEST_1',
        input_temp=25.5,
        output_temp=30.2,
        flow=15.3
    )
    
    print(f"데이터: {sensor_data}")
    print(f"유효성: {sensor_data.is_valid()}")
    print(f"온도 차이: {sensor_data.get_temp_diff()}°C")
    print(f"딕셔너리: {sensor_data.to_dict()}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. HeatpumpData 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 2] HeatpumpData")
    
    hp_data = HeatpumpData(
        device_id='HP_1',
        input_temp=25.5,
        output_temp=30.2,
        flow=15.3,
        energy=123.45
    )
    
    print(f"데이터: {hp_data}")
    print(f"COP: {hp_data.calculate_cop()}")
    print(f"딕셔너리: {hp_data.to_dict()}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. GroundpipeData 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 3] GroundpipeData")
    
    gp_data = GroundpipeData(
        device_id='GP_1',
        input_temp=20.1,
        output_temp=22.3,
        flow=10.5
    )
    
    print(f"데이터: {gp_data}")
    print(f"온도 차이: {gp_data.get_temp_diff()}°C")
    print(f"딕셔너리: {gp_data.to_dict()}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. DeviceConfig 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[테스트 4] DeviceConfig")
    
    config_dict = {
        'device_id': 'HP_1',
        'name': '히트펌프_1',
        'ip': '192.168.1.101',
        'port': 502,
        'description': '히트펌프_1',
        'enabled': True,
        'sensors': {
            'temp1_slave_id': 1,
            'temp2_slave_id': 2,
            'flow_slave_id': 3
        }
    }
    
    config = DeviceConfig.from_dict(config_dict)
    print(f"설정: {config}")
    print(f"딕셔너리: {config.to_dict()}")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
