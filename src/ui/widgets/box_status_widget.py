# ==============================================
# 플라스틱 함 상태 위젯
# ==============================================
"""
히트펌프/지중배관 실시간 상태 표시 위젯

기능:
- 실시간 온도/유량 표시
- 상태 색상 표시 (정상/경고/오류)
- 그래프 미리보기
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.theme import Theme


class BoxStatusWidget(QWidget):
    """플라스틱 함 상태 위젯"""
    
    def __init__(self, device_id: str, device_name: str, parent=None):
        """
        초기화
        
        Args:
            device_id: 장치 ID (예: 'HP_1')
            device_name: 장치 이름 (예: '히트펌프_1')
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
        group = QGroupBox(f'🌡️ {self.device_name}')
        group.setFont(Theme.font(11, bold=True))
        
        group_layout = QGridLayout()
        group_layout.setSpacing(10)
        
        # 입구 온도
        self.temp_in_label = QLabel('--')
        self.temp_in_label.setFont(Theme.font(14, bold=True))
        self.temp_in_label.setStyleSheet(f'color: {Theme.PRIMARY};')
        group_layout.addWidget(QLabel('입구:'), 0, 0)
        group_layout.addWidget(self.temp_in_label, 0, 1)
        group_layout.addWidget(QLabel('°C'), 0, 2)
        
        # 출구 온도
        self.temp_out_label = QLabel('--')
        self.temp_out_label.setFont(Theme.font(14, bold=True))
        self.temp_out_label.setStyleSheet(f'color: {Theme.SUCCESS};')
        group_layout.addWidget(QLabel('출구:'), 1, 0)
        group_layout.addWidget(self.temp_out_label, 1, 1)
        group_layout.addWidget(QLabel('°C'), 1, 2)
        
        # 유량
        self.flow_label = QLabel('--')
        self.flow_label.setFont(Theme.font(14, bold=True))
        self.flow_label.setStyleSheet(f'color: {Theme.WARNING};')
        group_layout.addWidget(QLabel('유량:'), 2, 0)
        group_layout.addWidget(self.flow_label, 2, 1)
        group_layout.addWidget(QLabel('L/min'), 2, 2)
        
        # 상태
        self.status_label = QLabel('🟢 정상')
        self.status_label.setFont(Theme.font(10))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(self.status_label, 3, 0, 1, 3)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        self.setLayout(layout)
    
    def update_data(self, temp_in: float, temp_out: float, flow: float):
        """
        데이터 업데이트
        
        Args:
            temp_in: 입구 온도
            temp_out: 출구 온도
            flow: 유량
        """
        self.temp_in_label.setText(f'{temp_in:.1f}')
        self.temp_out_label.setText(f'{temp_out:.1f}')
        self.flow_label.setText(f'{flow:.1f}')
        
        # 상태 판단 (예: 유량이 0이면 경고)
        if flow < 0.1:
            self.status_label.setText('🟡 유량 없음')
            self.status_label.setStyleSheet(f'color: {Theme.WARNING};')
        else:
            self.status_label.setText('🟢 정상')
            self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
