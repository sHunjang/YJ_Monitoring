# ==============================================
# 로그 뷰어 위젯
# ==============================================
"""
실시간 센서 데이터 로그 표시 위젯

기능:
- 센서 데이터 로그 표시
- 자동 스크롤
- 색상 구분 (센서 타입별)
- 최대 라인 수 제한
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QColor, QFont

from ui.theme import Theme

logger = logging.getLogger(__name__)


class LogViewerWidget(QWidget):
    """센서 데이터 로그 뷰어 위젯"""
    
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
        self.line_count = 0  # 라인 번호
        
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
        
        # 필터 (센서 타입별)
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
        
        # 폰트 크기
        log_font = QFont('Consolas', 11)  # 11pt로 증가
        self.log_text.setFont(log_font)
        
        # 라인 랩 모드 설정
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # 스타일시트
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.BG_SECONDARY};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
                padding: 15px;
                line-height: 160%;
            }}
        """)
        
        layout.addWidget(self.log_text)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 하단 정보 바
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_layout = QHBoxLayout()
        
        self.info_label = QLabel('센서 데이터 대기 중...')
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
    
    def add_sensor_data_log(
        self,
        timestamp: datetime,
        sensor_type: str,
        device_id: str,
        data: dict
    ):
        """
        센서 데이터 로그 추가
        
        Args:
            timestamp: 타임스탬프
            sensor_type: 센서 타입 (HP, GP, ELEC)
            device_id: 장치 ID
            data: 센서 데이터 딕셔너리
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
        
        self.line_count += 1
        
        # 시간 포맷
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # 센서 타입별 아이콘과 색상
        sensor_styles = {
            'HP': {'icon': '🌡️', 'color': "#B47C28", 'name': '히트펌프'},
            'GP': {'icon': '🌊', 'color': "#1C6EB1", 'name': '지중배관'},
            'ELEC': {'icon': '⚡', 'color': "#B3A422", 'name': '전력량계'}
        }
        style = sensor_styles.get(sensor_type, {'icon': '📊', 'color': "#000000", 'name': '센서'})
        
        # 센서 타입별 데이터 포맷
        if sensor_type == 'HP':
            data_str = (
                f"입구 <span style='color: #000000; font-weight: bold;'>{data.get('input_temp', 0):.1f}°C</span> | "
                f"출구 <span style='color: #000000; font-weight: bold;'>{data.get('output_temp', 0):.1f}°C</span> | "
                f"유량 <span style='color: #000000; font-weight: bold;'>{data.get('flow', 0)}L</span>"
            )
        elif sensor_type == 'GP':
            data_str = (
                f"입구 <span style='color: #000000; font-weight: bold;'>{data.get('input_temp', 0):.1f}°C</span> | "
                f"출구 <span style='color: #000000; font-weight: bold;'>{data.get('output_temp', 0):.1f}°C</span> | "
                f"유량 <span style='color: #000000; font-weight: bold;'>{data.get('flow', 0)}L</span>"
            )
        elif sensor_type == 'ELEC':
            data_str = (
                f"전력량 <span style='color: #000000; font-weight: bold;'>{data.get('total_energy', 0):.2f} kWh</span>"
            )
        else:
            data_str = str(data)
        
        # HTML 포맷 (더 깔끔하게)
        html = f'''
        <div style="padding: 8px 0px; margin: 3px 0px; border-bottom: 1px solid rgba(255,255,255,0.05);">
            <span style="color: #90CAF9; font-size: 10pt;">{time_str}</span>
            <span style="color: {style['color']}; font-weight: bold; font-size: 11pt;"> {style['icon']} {style['name']}</span>
            <span style="color: {style['color']}; font-weight: bold; font-size: 11pt;"> [{device_id}]</span>
            <br/>
            <span style="color: #000000; font-size: 11pt; margin-left: 10px;">   {data_str}</span>
        </div>
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
        
        # 정보 레이블 업데이트
        self.info_label.setText(f'마지막 데이터: {time_str} | {style["icon"]} {device_id}')
    
    def add_sensor_error_log(
        self,
        timestamp: datetime,
        sensor_type: str,
        device_id: str,
        error_message: str
    ):
        """
        센서 에러 로그 추가
        
        Args:
            timestamp: 타임스탬프
            sensor_type: 센서 타입 (HP, GP, ELEC)
            device_id: 장치 ID
            error_message: 에러 메시지
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
        
        self.line_count += 1
        
        # 시간 포맷
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # 센서 타입별 아이콘과 색상
        sensor_styles = {
            'HP': {'icon': '🌡️', 'color': "#B8873E", 'name': '히트펌프'},
            'GP': {'icon': '🌊', 'color': "#3173AA", 'name': '지중배관'},
            'ELEC': {'icon': '⚡', 'color': "#AF9E00", 'name': '전력량계'}
        }
        style = sensor_styles.get(sensor_type, {'icon': '📊', 'color': "#000000", 'name': '센서'})
        
        # HTML 포맷 (에러 표시)
        html = f'''
        <div style="padding: 8px 0px; margin: 3px 0px; border-bottom: 1px solid rgba(255,255,255,0.05); background-color: rgba(239, 83, 80, 0.1);">
            <span style="color: #90CAF9; font-size: 10pt;">{time_str}</span>
            <span style="color: {style['color']}; font-weight: bold; font-size: 11pt;"> {style['icon']} {style['name']}</span>
            <span style="color: {style['color']}; font-weight: bold; font-size: 11pt;"> [{device_id}]</span>
            <br/>
            <span style="color: #EF5350; font-size: 11pt; margin-left: 10px;">   ❌ {error_message}</span>
        </div>
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
        
        # 정보 레이블 업데이트
        self.info_label.setText(f'마지막 데이터: {time_str} | ❌ {device_id} 에러')
    
    def limit_lines(self):
        """최대 라인 수 제한"""
        document = self.log_text.document()
        while document.blockCount() > self.max_lines * 2:  # HTML은 2줄씩 차지
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
        try:
            # 현재 자동 스크롤 상태 저장
            was_auto_scroll = self.auto_scroll
            
            # 텍스트 완전 초기화
            self.log_text.clear()
            self.log_text.setHtml('')
            
            # Document 갱신
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
            
            # 라인 카운트 초기화
            self.line_count = 0
            
            # 카운트 업데이트
            self.update_count()
            
            # 정보 레이블 업데이트
            self.info_label.setText('로그가 지워졌습니다.')
            
            # 자동 스크롤 복원
            self.auto_scroll = was_auto_scroll
            
        except Exception as e:
            logger.error(f"로그 지우기 오류: {e}", exc_info=True)
    
    def on_filter_changed(self, filter_text: str):
        """필터 변경"""
        self.info_label.setText(f'필터: {filter_text}')
    
    def update_count(self):
        """로그 라인 수 업데이트"""
        self.count_label.setText(f'{self.line_count:,} 줄')


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
            self.setWindowTitle('센서 데이터 로그 뷰어 테스트')
            self.setMinimumSize(1400, 800)
            
            # 로그 뷰어 생성
            self.log_viewer = LogViewerWidget('실시간 센서 데이터')
            self.setCentralWidget(self.log_viewer)
            
            # 타이머 - 센서 데이터 생성 시뮬레이션
            self.timer = QTimer()
            self.timer.timeout.connect(self.generate_sensor_data)
            self.timer.start(2000)  # 2초마다
        
        def generate_sensor_data(self):
            """테스트 센서 데이터 생성"""
            now = datetime.now()
            
            # 랜덤 센서 선택
            sensor_types = ['HP', 'GP', 'ELEC']
            sensor_type = random.choice(sensor_types)
            
            device_id = f'{sensor_type}_{random.randint(1, 4)}'
            
            # 90% 정상, 10% 에러
            if random.random() < 0.9:
                if sensor_type == 'HP':
                    data = {
                        'input_temp': random.uniform(18, 25),
                        'output_temp': random.uniform(18, 25),
                        'flow': random.uniform(5, 15)
                    }
                elif sensor_type == 'GP':
                    data = {
                        'input_temp': random.uniform(15, 20),
                        'output_temp': random.uniform(15, 20),
                        'flow': random.uniform(3, 12)
                    }
                else:
                    data = {
                        'total_energy': random.uniform(1000, 5000)
                    }
                
                self.log_viewer.add_sensor_data_log(now, sensor_type, device_id, data)
            else:
                # 에러 로그
                self.log_viewer.add_sensor_error_log(now, sensor_type, device_id, '통신 실패')
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
