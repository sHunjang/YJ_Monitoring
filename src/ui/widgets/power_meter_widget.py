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
    QGroupBox, QGridLayout, QSizePolicy
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
        # ✅ 크기 정책 설정
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 그룹박스
        group = QGroupBox(f'⚡ {self.device_name}')
        group.setFont(Theme.font(11, bold=True))
        
        # ✅ 그룹박스 크기 정책
        group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        group_layout = QGridLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(15, 15, 15, 15)
        
        # 전력량 레이블
        label_energy = QLabel('전력량:')
        label_energy.setFont(Theme.font(11))
        
        self.energy_label = QLabel('--')
        self.energy_label.setFont(Theme.font(16, bold=True))
        self.energy_label.setStyleSheet(f'color: {Theme.PRIMARY};')
        self.energy_label.setMinimumWidth(100)  # ✅ 최소 너비 설정
        self.energy_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        unit_energy = QLabel('kWh')
        unit_energy.setFont(Theme.font(11))
        
        group_layout.addWidget(label_energy, 0, 0)
        group_layout.addWidget(self.energy_label, 0, 1)
        group_layout.addWidget(unit_energy, 0, 2)
        
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
        # ✅ 소수점 둘째 자리까지 표시 및 adjustSize
        self.energy_label.setText(f'{total_energy:.2f}')
        self.energy_label.adjustSize()
        
        self.status_label.setText('🟢 정상')
        self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
    
    def set_error_state(self, error_msg: str = '연결 오류'):
        """
        오류 상태 설정
        
        Args:
            error_msg: 오류 메시지
        """
        self.energy_label.setText('--')
        
        self.status_label.setText(f'🔴 {error_msg}')
        self.status_label.setStyleSheet(f'color: {Theme.DANGER};')


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget
    from PyQt6.QtCore import QTimer
    import random
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('PowerMeterWidget 테스트')
            self.setMinimumSize(1000, 300)
            
            # 중앙 위젯
            central = QWidget()
            layout = QHBoxLayout()
            layout.setSpacing(15)
            
            # 위젯 생성
            self.widget1 = PowerMeterWidget('HP_1', '히트펌프_1 전력량')
            self.widget2 = PowerMeterWidget('HP_2', '히트펌프_2 전력량')
            self.widget3 = PowerMeterWidget('TOTAL', '전체 전력량')
            
            layout.addWidget(self.widget1)
            layout.addWidget(self.widget2)
            layout.addWidget(self.widget3)
            layout.addStretch()
            
            central.setLayout(layout)
            self.setCentralWidget(central)
            
            # 타이머 - 값 변경 시뮬레이션
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_values)
            self.timer.start(2000)  # 2초마다
        
        def update_values(self):
            """값 업데이트 시뮬레이션"""
            energy1 = round(random.uniform(1200.0, 1300.0), 2)
            energy2 = round(random.uniform(800.0, 900.0), 2)
            energy_total = round(random.uniform(2500.0, 2700.0), 2)
            
            self.widget1.update_data(energy1)
            self.widget2.update_data(energy2)
            self.widget3.update_data(energy_total)
            
            print(f"Updated: HP_1({energy1:.2f} kWh), HP_2({energy2:.2f} kWh), "
                  f"TOTAL({energy_total:.2f} kWh)")
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
