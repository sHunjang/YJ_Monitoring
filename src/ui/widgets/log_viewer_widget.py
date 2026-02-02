# ==============================================
# 로그 뷰어 위젯
# ==============================================
"""
실시간 로그 표시 위젯

기능:
- 센서 데이터 로그 표시
- 자동 스크롤
- 색상 구분 (센서 타입별)
- 최대 라인 수 제한
- 필터링
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor, QFont

from ui.theme import Theme

logger = logging.getLogger(__name__)


class LogViewerWidget(QWidget):
    """로그 뷰어 위젯"""
    
    # 시그널
    clear_requested = pyqtSignal()
    
    def __init__(self, title: str = '로그', parent=None):
        """
        초기화
        
        Args:
            title: 위젯 제목
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        self.title = title
        self.max_lines = 500  # 최대 로그 라인 수
        self.auto_scroll = True
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 상단 컨트롤 바
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        control_layout = QHBoxLayout()
        
        # 제목
        title_label = QLabel(self.title)
        title_label.setFont(Theme.font(14, bold=True))
        title_label.setStyleSheet(f'color: {Theme.TEXT_PRIMARY};')
        control_layout.addWidget(title_label)
        
        control_layout.addStretch()
        
        # 필터
        filter_label = QLabel('필터:')
        filter_label.setFont(Theme.font(10))
        control_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.setFont(Theme.font(10))
        self.filter_combo.addItems([
            '전체',
            '히트펌프',
            '지중배관',
            '전력량계'
        ])
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        control_layout.addWidget(self.filter_combo)
        
        # 자동 스크롤 토글
        self.auto_scroll_btn = QPushButton('📌')
        self.auto_scroll_btn.setFont(Theme.font(10))
        self.auto_scroll_btn.setFixedSize(35, 30)
        self.auto_scroll_btn.setToolTip('자동 스크롤 ON')
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        control_layout.addWidget(self.auto_scroll_btn)
        
        # 지우기 버튼
        clear_btn = QPushButton('🗑️')
        clear_btn.setFont(Theme.font(10))
        clear_btn.setFixedSize(35, 30)
        clear_btn.setToolTip('로그 지우기')
        clear_btn.clicked.connect(self.clear_logs)
        control_layout.addWidget(clear_btn)
        
        layout.addLayout(control_layout)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 로그 텍스트 영역
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_font = QFont('Consolas', 9)
        self.log_text.setFont(log_font)
        
        # 스타일시트
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.BG_SECONDARY};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        
        layout.addWidget(self.log_text)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 하단 정보 바
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_layout = QHBoxLayout()
        
        self.info_label = QLabel('로그 대기 중...')
        self.info_label.setFont(Theme.font(9))
        self.info_label.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; padding: 5px;')
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        
        self.count_label = QLabel('0 줄')
        self.count_label.setFont(Theme.font(9))
        self.count_label.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; padding: 5px;')
        info_layout.addWidget(self.count_label)
        
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
    
    def add_log(
        self,
        timestamp: datetime,
        level: str,
        sensor_type: str,
        device_id: str,
        message: str
    ):
        """
        로그 추가
        
        Args:
            timestamp: 타임스탬프
            level: 로그 레벨 (INFO, WARNING, ERROR)
            sensor_type: 센서 타입 (HP, GP, ELEC)
            device_id: 장치 ID
            message: 메시지
        """
        # 필터 확인
        current_filter = self.filter_combo.currentText()
        if current_filter != '전체':
            if current_filter == '히트펌프' and sensor_type != 'HP':
                return
            elif current_filter == '지중배관' and sensor_type != 'GP':
                return
            elif current_filter == '전력량계' and sensor_type != 'ELEC':
                return
        
        # 시간 포맷
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # 센서 타입별 색상
        type_colors = {
            'HP': Theme.HEATPUMP_COLOR,
            'GP': Theme.PIPE_COLOR,
            'ELEC': Theme.POWER_COLOR
        }
        type_color = type_colors.get(sensor_type, Theme.TEXT_PRIMARY)
        
        # 레벨별 색상
        level_colors = {
            'INFO': Theme.SUCCESS,
            'WARNING': Theme.WARNING,
            'ERROR': "#f44336"
        }
        level_color = level_colors.get(level, Theme.TEXT_PRIMARY)
        
        # HTML 포맷
        html = f'''
        <span style="color: {Theme.TEXT_SECONDARY};">{time_str}</span>
        <span style="color: {level_color};"> | {level:8s} | </span>
        <span style="color: {type_color};">sensors.{sensor_type.lower()}.reader.{device_id}</span>
        <span style="color: {Theme.TEXT_PRIMARY};"> | {message}</span>
        '''
        
        # 로그 추가
        self.log_text.append(html)
        
        # 최대 라인 수 제한
        self.limit_lines()
        
        # 자동 스크롤
        if self.auto_scroll:
            self.scroll_to_bottom()
        
        # 카운트 업데이트
        self.update_count()
    
    def add_sensor_data_log(
        self,
        timestamp: datetime,
        sensor_type: str,
        device_id: str,
        data: dict
    ):
        """
        센서 데이터 로그 추가 (포맷팅)
        
        Args:
            timestamp: 타임스탬프
            sensor_type: 센서 타입 (HP, GP, ELEC)
            device_id: 장치 ID
            data: 센서 데이터 딕셔너리
        """
        # 센서 타입별 메시지 포맷
        if sensor_type == 'HP':
            message = (
                f"[{device_id}] 센서 데이터 읽기 완료: "
                f"입구={data.get('input_temp', 0):.1f}°C, "
                f"출구={data.get('output_temp', 0):.1f}°C, "
                f"유량={data.get('flow', 0):.1f}L/min"
            )
        elif sensor_type == 'GP':
            message = (
                f"[{device_id}] 센서 데이터 읽기 완료: "
                f"입구={data.get('input_temp', 0):.1f}°C, "
                f"출구={data.get('output_temp', 0):.1f}°C, "
                f"유량={data.get('flow', 0):.1f}L/min"
            )
        elif sensor_type == 'ELEC':
            message = (
                f"[{device_id}] 센서 데이터 읽기 완료: "
                f"전력량={data.get('total_energy', 0):.2f}kWh"
            )
        else:
            message = f"[{device_id}] 센서 데이터 읽기 완료"
        
        self.add_log(timestamp, 'INFO', sensor_type, device_id, message)
    
    def limit_lines(self):
        """최대 라인 수 제한"""
        document = self.log_text.document()
        while document.lineCount() > self.max_lines:
            cursor = QTextCursor(document.firstBlock())
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # 줄바꿈 제거
    
    def scroll_to_bottom(self):
        """맨 아래로 스크롤"""
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def toggle_auto_scroll(self):
        """자동 스크롤 토글"""
        self.auto_scroll = self.auto_scroll_btn.isChecked()
        
        if self.auto_scroll:
            self.auto_scroll_btn.setToolTip('자동 스크롤 ON')
            self.scroll_to_bottom()
        else:
            self.auto_scroll_btn.setToolTip('자동 스크롤 OFF')
    
    def clear_logs(self):
        """로그 지우기"""
        self.log_text.clear()
        self.update_count()
        self.info_label.setText('로그가 지워졌습니다.')
    
    def on_filter_changed(self, filter_text: str):
        """필터 변경"""
        # 필터 변경 시 로그 재구성은 복잡하므로
        # 간단하게 메시지만 표시
        self.info_label.setText(f'필터: {filter_text} (새 로그부터 적용)')
    
    def update_count(self):
        """로그 라인 수 업데이트"""
        line_count = self.log_text.document().lineCount()
        self.count_label.setText(f'{line_count:,} 줄')


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtCore import QTimer
    import random
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('LogViewerWidget 테스트')
            self.setMinimumSize(1200, 700)
            
            # 로그 뷰어 생성
            self.log_viewer = LogViewerWidget('실시간 센서 로그')
            self.setCentralWidget(self.log_viewer)
            
            # 타이머 - 로그 생성 시뮬레이션
            self.timer = QTimer()
            self.timer.timeout.connect(self.generate_log)
            self.timer.start(1000)  # 1초마다
        
        def generate_log(self):
            """테스트 로그 생성"""
            now = datetime.now()
            
            # 랜덤 센서 선택
            sensor_types = ['HP', 'GP', 'ELEC']
            sensor_type = random.choice(sensor_types)
            
            device_id = f'{sensor_type}_{random.randint(1, 4)}'
            
            if sensor_type == 'HP':
                data = {
                    'input_temp': random.uniform(18, 25),
                    'output_temp': random.uniform(18, 25),
                    'flow': random.uniform(0, 10)
                }
            elif sensor_type == 'GP':
                data = {
                    'input_temp': random.uniform(15, 20),
                    'output_temp': random.uniform(15, 20),
                    'flow': random.uniform(0, 8)
                }
            else:
                data = {
                    'total_energy': random.uniform(100, 500)
                }
            
            self.log_viewer.add_sensor_data_log(now, sensor_type, device_id, data)
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
