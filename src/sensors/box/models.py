# ==============================================
# 플라스틱 함 센서 데이터 모델
# ==============================================
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BoxSensorData:
    device_id: str
    input_temp: Optional[float] = None
    output_temp: Optional[float] = None
    flow: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def is_valid(self):
        return any([self.input_temp is not None, self.output_temp is not None, self.flow is not None])

    def get_temp_diff(self):
        if self.input_temp is not None and self.output_temp is not None:
            return round(self.output_temp - self.input_temp, 2)
        return None

    def to_dict(self):
        return {'device_id': self.device_id, 'input_temp': self.input_temp,
                'output_temp': self.output_temp, 'flow': self.flow,
                'timestamp': self.timestamp.isoformat(), 'temp_diff': self.get_temp_diff()}

    def __str__(self):
        return (f"BoxSensorData(device_id='{self.device_id}', "
                f"T_in={self.input_temp}°C, T_out={self.output_temp}°C, flow={self.flow}L)")


@dataclass
class HeatpumpData(BoxSensorData):
    energy: Optional[float] = None

    def calculate_cop(self):
        if (self.flow is not None and self.input_temp is not None and
                self.output_temp is not None and self.energy is not None and self.energy > 0):
            temp_diff = self.output_temp - self.input_temp
            if abs(temp_diff) < 0.1:
                return None
            heat_output = (self.flow * temp_diff * 4.186) / 60
            cop = abs(heat_output / self.energy) if self.energy > 0 else None
            return round(cop, 2) if cop else None
        return None

    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({'energy': self.energy, 'cop': self.calculate_cop()})
        return base_dict

    def __str__(self):
        return (f"HeatpumpData(device_id='{self.device_id}', "
                f"T_in={self.input_temp}°C, T_out={self.output_temp}°C, "
                f"flow={self.flow}L, energy={self.energy}kWh)")


@dataclass
class GroundpipeData(BoxSensorData):
    def __str__(self):
        return (f"GroundpipeData(device_id='{self.device_id}', "
                f"T_in={self.input_temp}°C, T_out={self.output_temp}°C, flow={self.flow}L)")


@dataclass
class DeviceConfig:
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
    def from_dict(cls, data: dict):
        sensors = data.get('sensors', {})
        return cls(device_id=data.get('device_id', ''), name=data.get('name', ''),
                   ip=data.get('ip', ''), port=data.get('port', 502),
                   description=data.get('description', ''), enabled=data.get('enabled', True),
                   temp1_slave_id=sensors.get('temp1_slave_id', 1),
                   temp2_slave_id=sensors.get('temp2_slave_id', 2),
                   flow_slave_id=sensors.get('flow_slave_id', 3))

    def to_dict(self):
        return {'device_id': self.device_id, 'name': self.name, 'ip': self.ip,
                'port': self.port, 'description': self.description, 'enabled': self.enabled,
                'sensors': {'temp1_slave_id': self.temp1_slave_id,
                            'temp2_slave_id': self.temp2_slave_id,
                            'flow_slave_id': self.flow_slave_id}}

    def __str__(self):
        return f"DeviceConfig(device_id='{self.device_id}', name='{self.name}', ip='{self.ip}')"
