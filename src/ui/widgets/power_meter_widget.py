# ==============================================
# 전력량계 위젯
# ==============================================
"""
전력량계 실시간 표시 위젯

기능:
- 실시간 전력량 표시
- 누적 전력량 그래프
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.theme import Theme


class PowerMeterWidget(QWidget):
    """전력량계 위젯"""
    
    def __init__(self, device_id: str, device_name: str, parent=None):
        """
        초기화
        
        Args:
            device_id: 장치 ID (예: 'HP_1')
            device_name: 장치 이름 (예: '히트펌프_1 전력량')
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.device_id = device_id
        self.device_name = device_name
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 그룹박스
        group = QGroupBox(f'⚡ {self.device_name}')
        group.setFont(Theme.font(11, bold=True))
        
        group_layout = QGridLayout()
        group_layout.setSpacing(10)
        
        # 전력량
        self.energy_label = QLabel('--')
        self.energy_label.setFont(Theme.font(16, bold=True))
        self.energy_label.setStyleSheet(f'color: {Theme.PRIMARY};')
        group_layout.addWidget(QLabel('전력량:'), 0, 0)
        group_layout.addWidget(self.energy_label, 0, 1)
        group_layout.addWidget(QLabel('kWh'), 0, 2)
        
        # 상태
        self.status_label = QLabel('🟢 정상')
        self.status_label.setFont(Theme.font(10))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(self.status_label, 1, 0, 1, 3)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        self.setLayout(layout)
    
    def update_data(self, total_energy: float):
        """
        데이터 업데이트
        
        Args:
            total_energy: 누적 전력량
        """
        self.energy_label.setText(f'{total_energy:.1f}')
        self.status_label.setText('🟢 정상')
        self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
