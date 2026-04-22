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
    QGroupBox, QGridLayout, QSizePolicy
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
        # ✅ 크기 정책 설정
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 그룹박스
        group = QGroupBox(f'🌡️ {self.device_name}')
        group.setFont(Theme.font(11, bold=True))
        
        # ✅ 그룹박스 크기 정책
        group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        group_layout = QGridLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(15, 15, 15, 15)
        
        # 입구 온도
        label_in = QLabel('입구:')
        label_in.setFont(Theme.font(11))
        
        self.temp_in_label = QLabel('--')
        self.temp_in_label.setFont(Theme.font(14, bold=True))
        self.temp_in_label.setStyleSheet(f'color: {Theme.PRIMARY};')
        self.temp_in_label.setMinimumWidth(60)  # ✅ 최소 너비
        
        unit_in = QLabel('°C')
        unit_in.setFont(Theme.font(11))
        
        group_layout.addWidget(label_in, 0, 0)
        group_layout.addWidget(self.temp_in_label, 0, 1)
        group_layout.addWidget(unit_in, 0, 2)
        
        # 출구 온도
        label_out = QLabel('출구:')
        label_out.setFont(Theme.font(11))
        
        self.temp_out_label = QLabel('--')
        self.temp_out_label.setFont(Theme.font(14, bold=True))
        self.temp_out_label.setStyleSheet(f'color: {Theme.SUCCESS};')
        self.temp_out_label.setMinimumWidth(60)  # ✅ 최소 너비
        
        unit_out = QLabel('°C')
        unit_out.setFont(Theme.font(11))
        
        group_layout.addWidget(label_out, 1, 0)
        group_layout.addWidget(self.temp_out_label, 1, 1)
        group_layout.addWidget(unit_out, 1, 2)
        
        # 유량
        label_flow = QLabel('유량:')
        label_flow.setFont(Theme.font(11))
        
        self.flow_label = QLabel('--')
        self.flow_label.setFont(Theme.font(14, bold=True))
        self.flow_label.setStyleSheet(f'color: {Theme.WARNING};')
        self.flow_label.setMinimumWidth(60)  # ✅ 최소 너비
        
        unit_flow = QLabel('L')
        unit_flow.setFont(Theme.font(11))
        
        group_layout.addWidget(label_flow, 2, 0)
        group_layout.addWidget(self.flow_label, 2, 1)
        group_layout.addWidget(unit_flow, 2, 2)
        
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
        # ✅ 값 업데이트 시 adjustSize 호출
        self.temp_in_label.setText(f'{temp_in:.1f}')
        self.temp_in_label.adjustSize()
        
        self.temp_out_label.setText(f'{temp_out:.1f}')
        self.temp_out_label.adjustSize()
        
        self.flow_label.setText(f'{flow}')
        self.flow_label.adjustSize()
        
        # 상태 판단 (예: 유량이 0이면 경고)
        if flow < 0.1:
            self.status_label.setText('🟡 유량 없음')
            self.status_label.setStyleSheet(f'color: {Theme.WARNING};')
        else:
            self.status_label.setText('🟢 정상')
            self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
    
    def set_error_state(self, error_msg: str = '연결 오류'):
        """
        오류 상태 설정
        
        Args:
            error_msg: 오류 메시지
        """
        self.temp_in_label.setText('--')
        self.temp_out_label.setText('--')
        self.flow_label.setText('--')
        
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
            self.setWindowTitle('BoxStatusWidget 테스트')
            self.setMinimumSize(1000, 300)
            
            # 중앙 위젯
            central = QWidget()
            layout = QHBoxLayout()
            layout.setSpacing(15)
            
            # 위젯 생성
            self.widget1 = BoxStatusWidget('HP_1', '히트펌프_1')
            self.widget2 = BoxStatusWidget('HP_2', '히트펌프_2')
            self.widget3 = BoxStatusWidget('GP_1', '지중배관_1')
            
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
            temp1_in = round(random.uniform(20.0, 30.0), 1)
            temp1_out = round(random.uniform(25.0, 35.0), 1)
            flow1 = round(random.uniform(10.0, 20.0), 1)
            
            temp2_in = round(random.uniform(22.0, 28.0), 1)
            temp2_out = round(random.uniform(27.0, 33.0), 1)
            flow2 = round(random.uniform(0.0, 5.0), 1)  # 유량 낮음
            
            temp3_in = round(random.uniform(18.0, 25.0), 1)
            temp3_out = round(random.uniform(23.0, 30.0), 1)
            flow3 = round(random.uniform(15.0, 25.0), 1)
            
            self.widget1.update_data(temp1_in, temp1_out, flow1)
            self.widget2.update_data(temp2_in, temp2_out, flow2)
            self.widget3.update_data(temp3_in, temp3_out, flow3)
            
            print(f"Updated: HP_1({temp1_in:.1f}, {temp1_out:.1f}, {flow1}), "
                  f"HP_2({temp2_in:.1f}, {temp2_out:.1f}, {flow2}), "
                  f"GP_1({temp3_in:.1f}, {temp3_out:.1f}, {flow3})")
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
