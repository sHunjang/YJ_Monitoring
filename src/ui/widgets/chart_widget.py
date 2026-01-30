# ==============================================
# 차트 위젯
# ==============================================
"""
시계열 데이터 차트 위젯

기능:
- 시계열 데이터 시각화
- 줌/팬 기능
- 범례 표시
- 그리드 표시
"""

from datetime import datetime
from typing import List, Dict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import pyqtgraph as pg

from ui.theme import Theme


class ChartWidget(QWidget):
    """차트 위젯"""
    
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
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 제목
        title_label = QLabel(self.title)
        title_label.setFont(Theme.font(14, bold=True))
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                padding: 10px;
                background-color: transparent;
            }}
        """)
        layout.addWidget(title_label)
        
        # 차트 생성
        self.plot_widget = pg.PlotWidget()
        
        # 배경 및 스타일 설정
        self.plot_widget.setBackground(Theme.BG_SECONDARY)
        
        # 축 설정
        axis_pen = pg.mkPen(color=Theme.CHART_AXIS, width=1)
        self.plot_widget.getAxis('bottom').setPen(axis_pen)
        self.plot_widget.getAxis('left').setPen(axis_pen)
        
        # 그리드 설정
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # 범례 추가
        self.plot_widget.addLegend(
            offset=(10, 10),
            labelTextColor=Theme.TEXT_PRIMARY,
            brush=Theme.BG_SECONDARY,
            pen=pg.mkPen(color=Theme.BORDER, width=1)
        )
        
        # 마우스 인터랙션 활성화
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # 스타일시트
        self.plot_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
            }}
        """)
        
        layout.addWidget(self.plot_widget)
        
        self.setLayout(layout)
    
    def add_line(
        self,
        device_id: str,
        data: List[Dict],
        color: str = None,
        name: str = None
    ):
        """
        라인 추가
        
        Args:
            device_id: 장치 ID
            data: [{'timestamp': datetime, 'value': float}, ...]
            color: 라인 색상 (hex)
            name: 범례에 표시할 이름
        """
        if not data:
            return
        
        # 색상 기본값
        if color is None:
            color = Theme.CHART_LINE
        
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
        pen = pg.mkPen(color=color, width=2)
        line = self.plot_widget.plot(
            timestamps,
            values,
            pen=pen,
            name=name
        )
        
        self.plot_lines[device_id] = line
    
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
    
    def remove_line(self, device_id: str):
        """
        라인 제거
        
        Args:
            device_id: 장치 ID
        """
        if device_id in self.plot_lines:
            self.plot_widget.removeItem(self.plot_lines[device_id])
            del self.plot_lines[device_id]
    
    def clear(self):
        """모든 라인 제거"""
        for device_id in list(self.plot_lines.keys()):
            self.remove_line(device_id)
        
        self.plot_lines.clear()
    
    def set_x_axis_datetime(self):
        """X축을 날짜/시간 형식으로 설정"""
        axis = pg.DateAxisItem()
        self.plot_widget.setAxisItems({'bottom': axis})
    
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
            self.setWindowTitle('ChartWidget 테스트')
            self.setMinimumSize(1200, 600)
            
            # 차트 생성
            self.chart = ChartWidget('온도 추이')
            self.chart.set_labels(x_label='시간', y_label='온도 (°C)')
            self.chart.set_x_axis_datetime()
            
            self.setCentralWidget(self.chart)
            
            # 초기 데이터 생성
            self.generate_data()
            
            # 타이머 - 데이터 업데이트 시뮬레이션
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_data)
            self.timer.start(2000)  # 2초마다
        
        def generate_data(self):
            """초기 데이터 생성"""
            now = datetime.now()
            
            # HP_1 데이터
            data1 = []
            for i in range(60):
                data1.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 25.0 + random.uniform(-2, 2)
                })
            
            # HP_2 데이터
            data2 = []
            for i in range(60):
                data2.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 30.0 + random.uniform(-2, 2)
                })
            
            self.chart.add_line('HP_1', data1, color=Theme.HEATPUMP_COLOR, name='히트펌프 1')
            self.chart.add_line('HP_2', data2, color=Theme.PRIMARY, name='히트펌프 2')
        
        def update_data(self):
            """데이터 업데이트"""
            now = datetime.now()
            
            # HP_1 데이터
            data1 = []
            for i in range(60):
                data1.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 25.0 + random.uniform(-2, 2)
                })
            
            # HP_2 데이터
            data2 = []
            for i in range(60):
                data2.append({
                    'timestamp': now - timedelta(minutes=60-i),
                    'value': 30.0 + random.uniform(-2, 2)
                })
            
            self.chart.update_line('HP_1', data1)
            self.chart.update_line('HP_2', data2)
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
