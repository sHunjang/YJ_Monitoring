# ==============================================
# 센서 카드 위젯
# ==============================================
"""
센서 데이터 표시 카드 위젯

기능:
- 센서 이름 표시
- 실시간 값 표시
- 색상 구분 (타입별)
- 애니메이션 효과
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor

from ui.theme import Theme


class SensorCard(QWidget):
    """센서 카드 위젯"""
    
    def __init__(self, title: str, value: str = '0.0', color: str = Theme.PRIMARY, parent=None):
        """
        초기화
        
        Args:
            title: 카드 제목 (장치 ID)
            value: 초기 값
            color: 강조 색상
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        self.title = title
        self.color = color
        self._value = value
        
        self.init_ui()
        self.add_shadow_effect()
    
    def init_ui(self):
        """UI 초기화"""
        # ✅ 최소 크기만 설정 (최대 크기 제한 제거)
        self.setMinimumSize(220, 140)
        
        # ✅ 크기 정책 설정
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        # 배경 스타일
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 2px solid {self.color};
                border-radius: 15px;
            }}
        """)
        
        # 레이아웃
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 제목
        self.title_label = QLabel(self.title)
        self.title_label.setFont(Theme.font(12, bold=True))
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                background-color: transparent;
                border: none;
            }}
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)  # ✅ 제목 줄바꿈 허용
        layout.addWidget(self.title_label)
        
        # 구분선
        divider = QWidget()
        divider.setFixedHeight(2)
        divider.setStyleSheet(f"""
            background-color: {self.color};
            border: none;
            border-radius: 1px;
        """)
        layout.addWidget(divider)
        
        # 값 레이블
        self.value_label = QLabel(self._value)
        self.value_label.setFont(Theme.font(22, bold=True))
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                background-color: transparent;
                border: none;
                padding: 10px 5px;
            }}
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setWordWrap(False)  # 값은 한 줄로
        self.value_label.setMinimumHeight(50)  # ✅ 최소 높이
        
        # ✅ 값 레이블 크기 정책
        self.value_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
        layout.addWidget(self.value_label)
        
        # ✅ stretch 제거 (값 레이블이 충분한 공간 확보)
        # layout.addStretch() 제거
        
        self.setLayout(layout)
    
    def add_shadow_effect(self):
        """그림자 효과 추가"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)
    
    def update_value(self, value: str):
        """
        값 업데이트
        
        Args:
            value: 새 값
        """
        old_value = self._value
        self._value = value
        self.value_label.setText(value)
        
        # ✅ 크기 재조정
        # self.value_label.adjustSize()
        
        # ✅ 값이 실제로 변경되었을 때만 애니메이션
        if old_value != value:
            self.animate_value_change()
    
    def animate_value_change(self):
        """값 변경 애니메이션 - 단순화"""
        # ✅ 애니메이션 제거 (geometry 애니메이션이 텍스트 잘림 문제 유발)
        # 필요하면 opacity 애니메이션 등 다른 방식 사용
        pass
    
    def set_color(self, color: str):
        """
        색상 변경
        
        Args:
            color: 새 색상 (hex)
        """
        self.color = color
        
        # 스타일 업데이트
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 2px solid {self.color};
                border-radius: 15px;
            }}
        """)
        
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                background-color: transparent;
                border: none;
            }}
        """)
    
    def enterEvent(self, event):
        """마우스 호버 - 진입"""
        # 배경색 변경
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_TERTIARY};
                border: 2px solid {self.color};
                border-radius: 15px;
            }}
        """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """마우스 호버 - 나감"""
        # 배경색 원래대로
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 2px solid {self.color};
                border-radius: 15px;
            }}
        """)
        super().leaveEvent(event)


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
            self.setWindowTitle('SensorCard 테스트')
            self.setMinimumSize(1200, 300)
            
            # 중앙 위젯
            central = QWidget()
            layout = QHBoxLayout()
            layout.setSpacing(15)
            
            # 카드 생성 - 긴 텍스트로 테스트
            self.card1 = SensorCard('히트펌프_1', '25.5°C', Theme.HEATPUMP_COLOR)
            self.card2 = SensorCard('지중배관_10', '30.2°C', Theme.PIPE_COLOR)
            self.card3 = SensorCard('Total', '2621.48 kWh', Theme.POWER_COLOR)
            self.card4 = SensorCard('열풍기_1', '1234.56 kWh', Theme.POWER_COLOR)
            
            layout.addWidget(self.card1)
            layout.addWidget(self.card2)
            layout.addWidget(self.card3)
            layout.addWidget(self.card4)
            layout.addStretch()  # 오른쪽 여백
            
            central.setLayout(layout)
            self.setCentralWidget(central)
            
            # 타이머 - 값 변경 시뮬레이션
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_values)
            self.timer.start(2000)  # 2초마다
        
        def update_values(self):
            """값 업데이트 시뮬레이션"""
            temp1 = round(random.uniform(20.0, 30.0), 1)
            temp2 = round(random.uniform(25.0, 35.0), 1)
            energy1 = round(random.uniform(2600.0, 2700.0), 2)
            energy2 = round(random.uniform(1200.0, 1300.0), 2)
            
            self.card1.update_value(f'{temp1}°C')
            self.card2.update_value(f'{temp2}°C')
            self.card3.update_value(f'{energy1} kWh')
            self.card4.update_value(f'{energy2} kWh')
            
            print(f"Updated: {temp1}°C, {temp2}°C, {energy1} kWh, {energy2} kWh")
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
