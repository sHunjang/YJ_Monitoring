# ==============================================
# 차트 위젯 (개선 버전)
# ==============================================
"""
시계열 데이터 차트 위젯

기능:
- 시계열 데이터 시각화
- 줌/팬 기능
- 범례 표시
- 그리드 표시
- 십자선 커서
- 데이터 포인트 툴팁
- 시간 범위 선택
- 새로고침
- 자동 시간 포맷 (HH:MM → MM-DD)
"""

from datetime import datetime
from typing import List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal
import pyqtgraph as pg
from pyqtgraph import DateAxisItem

from ui.theme import Theme


class SmartDateAxisItem(DateAxisItem):
    """
    스마트 날짜 축
    
    줌 레벨에 따라 자동으로 포맷 변경:
    - 좁은 범위 (< 3시간): HH:MM
    - 중간 범위 (< 7일): MM-DD HH:MM
    - 넓은 범위 (>= 7일): MM-DD
    """
    
    def tickStrings(self, values, scale, spacing):
        """틱 레이블 문자열 생성"""
        if not values:
            return []
        
        # 시간 범위 계산 (초 단위)
        time_range = max(values) - min(values)
        
        strings = []
        for value in values:
            try:
                dt = datetime.fromtimestamp(value)
                
                # 범위에 따른 포맷 선택
                if time_range < 3 * 3600:  # 3시간 미만
                    # HH:MM 형식
                    string = dt.strftime('%H:%M')
                elif time_range < 24 * 3600:  # 24시간 미만
                    # HH:MM 형식
                    string = dt.strftime('%H:%M')
                elif time_range < 7 * 24 * 3600:  # 7일 미만
                    # MM-DD HH:MM 형식
                    string = dt.strftime('%m-%d\n%H:%M')
                else:  # 7일 이상
                    # MM-DD 형식
                    string = dt.strftime('%m-%d')
                
                strings.append(string)
            except:
                strings.append('')
        
        return strings


class ChartWidget(QWidget):
    """개선된 차트 위젯"""
    
    # 시그널
    refresh_requested = pyqtSignal()  # 새로고침 요청
    time_range_changed = pyqtSignal(int)  # 시간 범위 변경 (hours)
    
    def __init__(self, title: str = '차트', parent=None):
        """
        초기화
        
        Args:
            title: 차트 제목
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        self.title = title
        self.plot_lines = {}  # {device_id: PlotDataItem}
        self.current_time_range = 1  # 기본 1시간
        
        self.init_ui()
        
        # ✅ 초기 X축 범위 설정 (현재 시간 기준)
        self.set_initial_x_range()
    
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
        
        # 시간 범위 선택
        time_range_label = QLabel('시간 범위:')
        time_range_label.setFont(Theme.font(10))
        control_layout.addWidget(time_range_label)
        
        self.time_range_combo = QComboBox()
        self.time_range_combo.setFont(Theme.font(10))
        self.time_range_combo.addItems([
            '10분',
            '30분',
            '1시간',
            '3시간',
            '6시간',
            '12시간',
            '24시간',
            '3일',
            '7일'
        ])
        self.time_range_combo.setCurrentText('1시간')
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        control_layout.addWidget(self.time_range_combo)
        
        # 새로고침 버튼
        refresh_btn = QPushButton('🔄')
        refresh_btn.setFont(Theme.font(10))
        refresh_btn.setFixedSize(35, 30)
        refresh_btn.setToolTip('새로고침')
        refresh_btn.clicked.connect(self.on_refresh_clicked)
        control_layout.addWidget(refresh_btn)
        
        # 자동 범위 버튼
        auto_range_btn = QPushButton('⊡')
        auto_range_btn.setFont(Theme.font(10))
        auto_range_btn.setFixedSize(35, 30)
        auto_range_btn.setToolTip('자동 범위')
        auto_range_btn.clicked.connect(self.auto_range)
        control_layout.addWidget(auto_range_btn)
        
        layout.addLayout(control_layout)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 차트 생성
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': SmartDateAxisItem()})
        
        # 배경 및 스타일 설정
        self.plot_widget.setBackground(Theme.BG_SECONDARY)
        
        # 축 설정
        axis_pen = pg.mkPen(color=Theme.CHART_AXIS, width=1)
        self.plot_widget.getAxis('bottom').setPen(axis_pen)
        self.plot_widget.getAxis('left').setPen(axis_pen)
        
        # 축 텍스트 색상
        self.plot_widget.getAxis('bottom').setTextPen(Theme.TEXT_PRIMARY)
        self.plot_widget.getAxis('left').setTextPen(Theme.TEXT_PRIMARY)
        
        # 그리드 설정
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 범례 추가
        self.legend = self.plot_widget.addLegend(
            offset=(10, 10),
            labelTextColor=Theme.TEXT_PRIMARY,
            brush=pg.mkBrush(Theme.BG_SECONDARY),
            pen=pg.mkPen(color=Theme.BORDER, width=1)
        )
        
        # 마우스 인터랙션 활성화
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # 십자선 커서 추가
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(Theme.PRIMARY, width=1, style=Qt.PenStyle.DashLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(Theme.PRIMARY, width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)
        
        # 마우스 이동 이벤트
        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self.on_mouse_moved
        )
        
        # 스타일시트
        self.plot_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
            }}
        """)
        
        layout.addWidget(self.plot_widget)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 하단 정보 바
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        info_layout = QHBoxLayout()
        
        self.info_label = QLabel('데이터를 불러오는 중...')
        self.info_label.setFont(Theme.font(9))
        self.info_label.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; padding: 5px;')
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        
        self.cursor_label = QLabel('')
        self.cursor_label.setFont(Theme.font(9))
        self.cursor_label.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; padding: 5px;')
        info_layout.addWidget(self.cursor_label)
        
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
    
    def set_initial_x_range(self):
        """✅ 초기 X축 범위 설정 (현재 시간 기준)"""
        now = datetime.now().timestamp()
        time_range_seconds = self.current_time_range * 3600
        self.plot_widget.setXRange(now - time_range_seconds, now, padding=0.02)
    
    def on_time_range_changed(self, text: str):
        """시간 범위 변경"""
        time_map = {
            '10분': 10/60,
            '30분': 0.5,
            '1시간': 1,
            '3시간': 3,
            '6시간': 6,
            '12시간': 12,
            '24시간': 24,
            '3일': 72,
            '7일': 168
        }
        
        hours = time_map.get(text, 1)
        self.current_time_range = hours
        
        # ✅ X축 범위 업데이트
        if self.plot_lines:
            # 데이터가 있으면 최신 데이터 기준
            latest_time = None
            for line in self.plot_lines.values():
                data = line.getData()
                if data[0] is not None and len(data[0]) > 0:
                    line_latest = max(data[0])
                    if latest_time is None or line_latest > latest_time:
                        latest_time = line_latest
            
            if latest_time:
                time_range_seconds = self.current_time_range * 3600
                self.plot_widget.setXRange(latest_time - time_range_seconds, latest_time, padding=0.02)
        else:
            # 데이터가 없으면 현재 시간 기준
            self.set_initial_x_range()
        
        self.time_range_changed.emit(int(hours * 60))  # 분 단위로 전달
    
    def on_refresh_clicked(self):
        """새로고침 버튼 클릭"""
        # ✅ 현재 시간 기준으로 X축 재설정
        self.set_initial_x_range()
        # 새로고침 시그널 발생
        self.refresh_requested.emit()
    
    def on_mouse_moved(self, evt):
        """마우스 이동 이벤트"""
        pos = evt[0]
        
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            
            # 십자선 업데이트
            self.v_line.setPos(mouse_point.x())
            self.h_line.setPos(mouse_point.y())
            
            # 커서 위치 정보 표시
            try:
                time_str = datetime.fromtimestamp(mouse_point.x()).strftime('%Y-%m-%d %H:%M:%S')
                value_str = f'{mouse_point.y():.2f}'
                self.cursor_label.setText(f'시간: {time_str} | 값: {value_str}')
            except:
                self.cursor_label.setText('')
    
    def add_line(
        self,
        device_id: str,
        data: List[Dict],
        color: str = None,
        name: str = None,
        width: int = 2
    ):
        """
        라인 추가
        
        Args:
            device_id: 장치 ID
            data: [{'timestamp': datetime, 'value': float}, ...]
            color: 라인 색상 (hex)
            name: 범례에 표시할 이름
            width: 라인 두께
        """
        if not data:
            self.update_info()
            return
        
        # 색상 기본값
        if color is None:
            # 장치별 자동 색상 할당
            colors = [
                Theme.PRIMARY,
                Theme.HEATPUMP_COLOR,
                Theme.PIPE_COLOR,
                Theme.WARNING,
                '#9c27b0',
                '#00bcd4',
                '#ff9800'
            ]
            color_idx = len(self.plot_lines) % len(colors)
            color = colors[color_idx]
        
        # 이름 기본값
        if name is None:
            name = device_id
        
        # 타임스탬프를 초 단위로 변환
        timestamps = []
        values = []
        
        for point in data:
            if isinstance(point['timestamp'], datetime):
                ts = point['timestamp'].timestamp()
            else:
                ts = point['timestamp']
            
            timestamps.append(ts)
            values.append(point['value'])
        
        # 기존 라인이 있으면 제거
        if device_id in self.plot_lines:
            self.plot_widget.removeItem(self.plot_lines[device_id])
        
        # 새 라인 추가
        pen = pg.mkPen(color=color, width=width)
        line = self.plot_widget.plot(
            timestamps,
            values,
            pen=pen,
            name=name,
            symbol='o',
            symbolSize=4,
            symbolBrush=color
        )
        
        self.plot_lines[device_id] = line
        
        # 정보 업데이트
        self.update_info()
        
        # ✅ X축 범위를 최신 데이터 기준으로 설정
        if timestamps:
            latest_time = max(timestamps)
            time_range_seconds = self.current_time_range * 3600
            self.plot_widget.setXRange(latest_time - time_range_seconds, latest_time, padding=0.02)
    
    def update_line(self, device_id: str, data: List[Dict]):
        """
        라인 데이터 업데이트
        
        Args:
            device_id: 장치 ID
            data: [{'timestamp': datetime, 'value': float}, ...]
        """
        if device_id not in self.plot_lines:
            return
        
        if not data:
            return
        
        # 타임스탬프를 초 단위로 변환
        timestamps = []
        values = []
        
        for point in data:
            if isinstance(point['timestamp'], datetime):
                ts = point['timestamp'].timestamp()
            else:
                ts = point['timestamp']
            
            timestamps.append(ts)
            values.append(point['value'])
        
        # 라인 업데이트
        self.plot_lines[device_id].setData(timestamps, values)
        
        # ✅ X축 범위를 최신 데이터 기준으로 설정
        if timestamps:
            latest_time = max(timestamps)
            time_range_seconds = self.current_time_range * 3600
            self.plot_widget.setXRange(latest_time - time_range_seconds, latest_time, padding=0.02)
        
        # 정보 업데이트
        self.update_info()
    
    def remove_line(self, device_id: str):
        """
        라인 제거
        
        Args:
            device_id: 장치 ID
        """
        if device_id in self.plot_lines:
            self.plot_widget.removeItem(self.plot_lines[device_id])
            del self.plot_lines[device_id]
            self.update_info()
    
    def clear(self):
        """모든 라인 제거"""
        for device_id in list(self.plot_lines.keys()):
            self.remove_line(device_id)
        
        self.plot_lines.clear()
        self.info_label.setText('데이터를 불러오는 중...')
    
    def set_labels(self, x_label: str = None, y_label: str = None):
        """
        축 레이블 설정
        
        Args:
            x_label: X축 레이블
            y_label: Y축 레이블
        """
        if x_label:
            self.plot_widget.setLabel('bottom', x_label, color=Theme.TEXT_PRIMARY)
        
        if y_label:
            self.plot_widget.setLabel('left', y_label, color=Theme.TEXT_PRIMARY)
    
    def auto_range(self):
        """자동 범위 조정"""
        self.plot_widget.autoRange()
    
    def update_info(self):
        """정보 라벨 업데이트"""
        line_count = len(self.plot_lines)
        
        if line_count == 0:
            self.info_label.setText('데이터 없음')
        else:
            # 총 데이터 포인트 수 계산
            total_points = 0
            for line in self.plot_lines.values():
                data = line.getData()
                if data[0] is not None:
                    total_points += len(data[0])
            
            self.info_label.setText(
                f'라인: {line_count}개 | 데이터 포인트: {total_points:,}개 | '
                f'시간 범위: {self.time_range_combo.currentText()}'
            )


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtCore import QTimer
    from datetime import timedelta
    import random
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('개선된 ChartWidget 테스트')
            self.setMinimumSize(1400, 700)
            
            # 차트 생성
            self.chart = ChartWidget('온도 추이')
            self.chart.set_labels(x_label='시간', y_label='온도 (°C)')
            
            # 새로고침 시그널 연결
            self.chart.refresh_requested.connect(self.update_data)
            self.chart.time_range_changed.connect(lambda mins: print(f'시간 범위 변경: {mins}분'))
            
            self.setCentralWidget(self.chart)
            
            # 3초 후 데이터 로드
            QTimer.singleShot(3000, self.generate_data)
            
            # 타이머 - 데이터 업데이트 시뮬레이션
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_data)
            self.timer.start(5000)  # 5초마다
        
        def generate_data(self):
            """초기 데이터 생성"""
            now = datetime.now()
            
            # HP_1 데이터
            data1 = []
            for i in range(60):
                data1.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 25.0 + random.uniform(-2, 2) + i * 0.05
                })
            
            # HP_2 데이터
            data2 = []
            for i in range(60):
                data2.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 30.0 + random.uniform(-2, 2) - i * 0.03
                })
            
            # HP_3 데이터
            data3 = []
            for i in range(60):
                data3.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 28.0 + random.uniform(-1, 1)
                })
            
            self.chart.add_line('HP_1', data1, color=Theme.HEATPUMP_COLOR, name='히트펌프 1')
            self.chart.add_line('HP_2', data2, color=Theme.PRIMARY, name='히트펌프 2')
            self.chart.add_line('HP_3', data3, color=Theme.PIPE_COLOR, name='히트펌프 3')
        
        def update_data(self):
            """데이터 업데이트"""
            now = datetime.now()
            
            # HP_1 데이터
            data1 = []
            for i in range(60):
                data1.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 25.0 + random.uniform(-2, 2) + i * 0.05
                })
            
            # HP_2 데이터
            data2 = []
            for i in range(60):
                data2.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 30.0 + random.uniform(-2, 2) - i * 0.03
                })
            
            # HP_3 데이터
            data3 = []
            for i in range(60):
                data3.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 28.0 + random.uniform(-1, 1)
                })
            
            self.chart.update_line('HP_1', data1)
            self.chart.update_line('HP_2', data2)
            self.chart.update_line('HP_3', data3)
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
