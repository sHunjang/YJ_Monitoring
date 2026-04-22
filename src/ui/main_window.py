# ==============================================
# 메인 윈도우
# ==============================================
"""
여주 센서 모니터링 시스템 메인 윈도우

기능:
- 실시간 데이터 모니터링
- 차트 표시
- 로그 뷰어
- 설정 관리
- CSV 내보내기
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QMessageBox,
    QMenuBar, QMenu, QGridLayout, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from ui.theme import Theme
from ui.widgets.sensor_card import SensorCard
from ui.widgets.chart_widget import ChartWidget
from ui.widgets.log_viewer_widget import LogViewerWidget
from ui.widgets.cop_tab_widget import CopTabWidget
from ui.dialogs.layout_map_dialog import LayoutMapDialog
from ui.dialogs import IPConfigDialog, PowerMeterConfigDialog, CSVExportDialog
from services.ui_data_service import UIDataService

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        """초기화"""
        super().__init__()
        
        self.setWindowTitle('여주 센서 모니터링 시스템 v1.0.0')
        self.setMinimumSize(1400, 900)
        
        # 데이터 서비스
        self.data_service = UIDataService()
        
        # 마지막 로그 타임스탬프 추적
        self.last_log_timestamps = {}   # {device_id: timestamp}
        
        # UI 초기화
        self.init_ui()
        
        # 타이머 설정 (5초마다 데이터 갱신)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)  # 5초
        
        # 초기 데이터 로드
        self.update_data()
        
        logger.info("MainWindow 초기화 완료")
    
    def init_ui(self):
        """UI 초기화"""
        # 메뉴바 생성
        self.create_menu_bar()
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 헤더
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        header_layout = QHBoxLayout()
        
        # 타이틀
        title = QLabel('🏭 여주 센서 모니터링 시스템')
        title.setFont(Theme.font(20, bold=True))
        title.setStyleSheet(f'color: {Theme.PRIMARY};')
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 상태 표시
        self.status_label = QLabel('● 연결됨')
        self.status_label.setFont(Theme.font(11))
        self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 탭 위젯
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.tabs = QTabWidget()
        self.tabs.setFont(Theme.font(11))
        
        # 탭 1: 대시보드
        dashboard_tab = self.create_dashboard_tab()
        self.tabs.addTab(dashboard_tab, '📊 대시보드')
        
        # 탭 2: 히트펌프
        heatpump_tab = self.create_heatpump_tab()
        self.tabs.addTab(heatpump_tab, '🌡️ 히트펌프')
        
        # 탭 3: 지중배관
        groundpipe_tab = self.create_groundpipe_tab()
        self.tabs.addTab(groundpipe_tab, '🌊 지중배관')
        
        # 탭 4: 전력량계
        power_tab = self.create_power_tab()
        self.tabs.addTab(power_tab, '⚡ 전력량계')

        # 탭 5: COP
        self.cop_tab = CopTabWidget(self.data_service)
        self.tabs.addTab(self.cop_tab, '📈 COP')
        
        main_layout.addWidget(self.tabs)
        
        central_widget.setLayout(main_layout)
    
    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 파일 메뉴
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        file_menu = menubar.addMenu('파일')
        
        # CSV 내보내기
        export_action = QAction('📥 CSV 내보내기', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.open_csv_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 종료
        exit_action = QAction('종료', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 설정 메뉴
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        settings_menu = menubar.addMenu('설정')
        
        layout_map_action = QAction('🏭 배치도', self)
        layout_map_action.triggered.connect(self.open_layout_map)
        settings_menu.addAction(layout_map_action)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 도움말 메뉴
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        help_menu = menubar.addMenu('도움말')
        
        # 정보
        about_action = QAction('프로그램 정보', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_dashboard_tab(self):
        """대시보드 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 요약 카드
        summary_layout = QHBoxLayout()
        
        self.hp_summary_card = SensorCard('히트펌프', '0개', Theme.HEATPUMP_COLOR)
        summary_layout.addWidget(self.hp_summary_card)
        
        self.gp_summary_card = SensorCard('지중배관', '0개', Theme.PIPE_COLOR)
        summary_layout.addWidget(self.gp_summary_card)
        
        self.power_summary_card = SensorCard('전력량계', '0개', Theme.POWER_COLOR)
        summary_layout.addWidget(self.power_summary_card)
        
        layout.addLayout(summary_layout)
        
        # 로그 뷰어
        self.log_viewer = LogViewerWidget('실시간 센서 로그')
        layout.addWidget(self.log_viewer)
        
        widget.setLayout(layout)
        return widget
    
    def create_heatpump_tab(self):
        """히트펌프 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 장치 선택 드롭다운
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        control_layout = QHBoxLayout()
        
        device_label = QLabel('장치 선택:')
        device_label.setFont(Theme.font(12, bold=True))
        control_layout.addWidget(device_label)
        
        self.hp_device_combo = QComboBox()
        self.hp_device_combo.setFont(Theme.font(11))
        self.hp_device_combo.setMinimumWidth(200)
        self.hp_device_combo.currentTextChanged.connect(self.on_hp_device_changed)
        control_layout.addWidget(self.hp_device_combo)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 센서 카드 (3개: 입구/출구/유량)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        self.hp_card_in = SensorCard('입구 온도', '0.0°C', Theme.HEATPUMP_COLOR)
        self.hp_card_out = SensorCard('출구 온도', '0.0°C', Theme.PRIMARY)
        self.hp_card_flow = SensorCard('유량', '0.0 L/min', Theme.WARNING)
        
        cards_layout.addWidget(self.hp_card_in)
        cards_layout.addWidget(self.hp_card_out)
        cards_layout.addWidget(self.hp_card_flow)
        
        layout.addLayout(cards_layout)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 차트
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.heatpump_chart = ChartWidget('히트펌프 온도/유량 추이')
        self.heatpump_chart.set_labels(y_label='값')
        layout.addWidget(self.heatpump_chart, stretch=1)
        
        widget.setLayout(layout)
        return widget


    
    def create_groundpipe_tab(self):
        """지중배관 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 장치 선택 드롭다운
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        control_layout = QHBoxLayout()
        
        device_label = QLabel('장치 선택:')
        device_label.setFont(Theme.font(12, bold=True))
        control_layout.addWidget(device_label)
        
        self.gp_device_combo = QComboBox()
        self.gp_device_combo.setFont(Theme.font(11))
        self.gp_device_combo.setMinimumWidth(200)
        self.gp_device_combo.currentTextChanged.connect(self.on_gp_device_changed)
        control_layout.addWidget(self.gp_device_combo)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 센서 카드 (3개: 입구/출구/유량)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        self.gp_card_in = SensorCard('입구 온도', '0.0°C', Theme.PIPE_COLOR)
        self.gp_card_out = SensorCard('출구 온도', '0.0°C', Theme.PRIMARY)
        self.gp_card_flow = SensorCard('유량', '0.0 L/min', Theme.WARNING)
        
        cards_layout.addWidget(self.gp_card_in)
        cards_layout.addWidget(self.gp_card_out)
        cards_layout.addWidget(self.gp_card_flow)
        
        layout.addLayout(cards_layout)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 차트
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.groundpipe_chart = ChartWidget('지중배관 온도/유량 추이')
        self.groundpipe_chart.set_labels(y_label='값')
        layout.addWidget(self.groundpipe_chart, stretch=1)
        
        widget.setLayout(layout)
        return widget

    def on_hp_device_changed(self, device_id: str):
        """히트펌프 장치 선택 변경"""
        if not device_id:
            return
        
        try:
            # 카드 업데이트
            stats_in = self.data_service.get_statistics_heatpump(device_id, hours=1, field='t_in')
            stats_out = self.data_service.get_statistics_heatpump(device_id, hours=1, field='t_out')
            stats_flow = self.data_service.get_statistics_heatpump(device_id, hours=1, field='flow')
            
            self.hp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
            self.hp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
            self.hp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")
            
            # 차트 클리어 후 재구성
            self.heatpump_chart.clear()
            
            # 입구 온도
            data_in = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='t_in')
            if data_in:
                self.heatpump_chart.add_line(
                    f'{device_id}_in',
                    data_in,
                    color=Theme.HEATPUMP_COLOR,
                    name='입구 온도'
                )
            
            # 출구 온도
            data_out = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='t_out')
            if data_out:
                self.heatpump_chart.add_line(
                    f'{device_id}_out',
                    data_out,
                    color=Theme.PRIMARY,
                    name='출구 온도'
                )
            
            # 유량
            data_flow = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='flow')
            if data_flow:
                self.heatpump_chart.add_line(
                    f'{device_id}_flow',
                    data_flow,
                    color=Theme.WARNING,
                    name='유량',
                    width=1
                )
        
        except Exception as e:
            logger.error(f"히트펌프 장치 변경 오류: {e}", exc_info=True)


    def on_gp_device_changed(self, device_id: str):
        """지중배관 장치 선택 변경"""
        if not device_id:
            return
        
        try:
            # 카드 업데이트
            stats_in = self.data_service.get_statistics_groundpipe(device_id, hours=1, field='t_in')
            stats_out = self.data_service.get_statistics_groundpipe(device_id, hours=1, field='t_out')
            stats_flow = self.data_service.get_statistics_groundpipe(device_id, hours=1, field='flow')
            
            self.gp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
            self.gp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
            self.gp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")
            
            # 차트 클리어 후 재구성
            self.groundpipe_chart.clear()
            
            # 입구 온도
            data_in = self.data_service.get_timeseries_groundpipe(device_id, hours=1, field='t_in')
            if data_in:
                self.groundpipe_chart.add_line(
                    f'{device_id}_in',
                    data_in,
                    color=Theme.PIPE_COLOR,
                    name='입구 온도'
                )
            
            # 출구 온도
            data_out = self.data_service.get_timeseries_groundpipe(device_id, hours=1, field='t_out')
            if data_out:
                self.groundpipe_chart.add_line(
                    f'{device_id}_out',
                    data_out,
                    color=Theme.PRIMARY,
                    name='출구 온도'
                )
            
            # 유량
            data_flow = self.data_service.get_timeseries_groundpipe(device_id, hours=1, field='flow')
            if data_flow:
                self.groundpipe_chart.add_line(
                    f'{device_id}_flow',
                    data_flow,
                    color=Theme.WARNING,
                    name='유량',
                    width=1
                )
        
        except Exception as e:
            logger.error(f"지중배관 장치 변경 오류: {e}", exc_info=True)

    
    def create_power_tab(self):
        """전력량계 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 센서 카드
        self.power_cards = []
        cards_layout = QHBoxLayout()
        
        # 전력량계 장치 목록 가져오기
        devices = self.data_service.get_all_power_devices()
        
        for device_id in devices[:4]:  # 최대 4개
            card = SensorCard(device_id, '0.0 kWh', Theme.POWER_COLOR)
            self.power_cards.append(card)
            cards_layout.addWidget(card)
        
        layout.addLayout(cards_layout)
        
        # 차트
        self.power_chart = ChartWidget('전력량 추이')
        self.power_chart.set_labels(y_label='전력량 (kWh)')
        layout.addWidget(self.power_chart)
        
        widget.setLayout(layout)
        return widget
    
    def update_data(self):
        """데이터 갱신"""
        try:
            now = datetime.now()
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 히트펌프 데이터 갱신
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            hp_devices = self.data_service.get_all_heatpump_devices()
            
            # ✅✅ 드롭다운 업데이트 (변경 시에만)
            current_hp_items = [self.hp_device_combo.itemText(i) for i in range(self.hp_device_combo.count())]
            if current_hp_items != hp_devices:
                current_selection = self.hp_device_combo.currentText()
                self.hp_device_combo.blockSignals(True)
                self.hp_device_combo.clear()
                self.hp_device_combo.addItems(hp_devices)
                
                # 이전 선택 복원 또는 첫 번째 선택
                if current_selection in hp_devices:
                    self.hp_device_combo.setCurrentText(current_selection)
                elif hp_devices:
                    self.hp_device_combo.setCurrentIndex(0)
                
                self.hp_device_combo.blockSignals(False)
            
            # ✅✅ 선택된 장치 업데이트
            selected_hp = self.hp_device_combo.currentText()
            if selected_hp:
                # 카드 업데이트
                stats_in = self.data_service.get_statistics_heatpump(selected_hp, hours=1, field='t_in')
                stats_out = self.data_service.get_statistics_heatpump(selected_hp, hours=1, field='t_out')
                stats_flow = self.data_service.get_statistics_heatpump(selected_hp, hours=1, field='flow')
                
                self.hp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
                self.hp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
                self.hp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")
                
                # 차트 업데이트 (update_line 사용)
                data_in = self.data_service.get_timeseries_heatpump(selected_hp, hours=1, field='t_in')
                if data_in:
                    if f'{selected_hp}_in' in self.heatpump_chart.plot_lines:
                        self.heatpump_chart.update_line(f'{selected_hp}_in', data_in)
                    else:
                        self.heatpump_chart.add_line(f'{selected_hp}_in', data_in, color=Theme.HEATPUMP_COLOR, name='입구 온도')
                
                data_out = self.data_service.get_timeseries_heatpump(selected_hp, hours=1, field='t_out')
                if data_out:
                    if f'{selected_hp}_out' in self.heatpump_chart.plot_lines:
                        self.heatpump_chart.update_line(f'{selected_hp}_out', data_out)
                    else:
                        self.heatpump_chart.add_line(f'{selected_hp}_out', data_out, color=Theme.PRIMARY, name='출구 온도')
                
                data_flow = self.data_service.get_timeseries_heatpump(selected_hp, hours=1, field='flow')
                if data_flow:
                    if f'{selected_hp}_flow' in self.heatpump_chart.plot_lines:
                        self.heatpump_chart.update_line(f'{selected_hp}_flow', data_flow)
                    else:
                        self.heatpump_chart.add_line(f'{selected_hp}_flow', data_flow, color=Theme.WARNING, name='유량', width=1)
                
                # 로그 추가
                timeseries = self.data_service.get_timeseries_heatpump(selected_hp, hours=1, field='t_in')
                if timeseries and len(timeseries) > 0:
                    latest_timestamp = timeseries[-1]['timestamp']
                    last_logged = self.last_log_timestamps.get(f'HP_{selected_hp}')
                    
                    if last_logged is None or latest_timestamp > last_logged:
                        data = {
                            'input_temp': stats_in['latest'],
                            'output_temp': stats_out['latest'],
                            'flow': stats_flow['latest']
                        }
                        self.log_viewer.add_sensor_data_log(latest_timestamp, 'HP', selected_hp, data)
                        self.last_log_timestamps[f'HP_{selected_hp}'] = latest_timestamp
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 지중배관 데이터 갱신
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            gp_devices = self.data_service.get_all_groundpipe_devices()
            
            # ✅✅ 드롭다운 업데이트 (변경 시에만)
            current_gp_items = [self.gp_device_combo.itemText(i) for i in range(self.gp_device_combo.count())]
            if current_gp_items != gp_devices:
                current_selection = self.gp_device_combo.currentText()
                self.gp_device_combo.blockSignals(True)
                self.gp_device_combo.clear()
                self.gp_device_combo.addItems(gp_devices)
                
                # 이전 선택 복원 또는 첫 번째 선택
                if current_selection in gp_devices:
                    self.gp_device_combo.setCurrentText(current_selection)
                elif gp_devices:
                    self.gp_device_combo.setCurrentIndex(0)
                
                self.gp_device_combo.blockSignals(False)
            
            # ✅✅ 선택된 장치 업데이트
            selected_gp = self.gp_device_combo.currentText()
            if selected_gp:
                # 카드 업데이트
                stats_in = self.data_service.get_statistics_groundpipe(selected_gp, hours=1, field='t_in')
                stats_out = self.data_service.get_statistics_groundpipe(selected_gp, hours=1, field='t_out')
                stats_flow = self.data_service.get_statistics_groundpipe(selected_gp, hours=1, field='flow')
                
                self.gp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
                self.gp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
                self.gp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")
                
                # 차트 업데이트 (update_line 사용)
                data_in = self.data_service.get_timeseries_groundpipe(selected_gp, hours=1, field='t_in')
                if data_in:
                    if f'{selected_gp}_in' in self.groundpipe_chart.plot_lines:
                        self.groundpipe_chart.update_line(f'{selected_gp}_in', data_in)
                    else:
                        self.groundpipe_chart.add_line(f'{selected_gp}_in', data_in, color=Theme.PIPE_COLOR, name='입구 온도')
                
                data_out = self.data_service.get_timeseries_groundpipe(selected_gp, hours=1, field='t_out')
                if data_out:
                    if f'{selected_gp}_out' in self.groundpipe_chart.plot_lines:
                        self.groundpipe_chart.update_line(f'{selected_gp}_out', data_out)
                    else:
                        self.groundpipe_chart.add_line(f'{selected_gp}_out', data_out, color=Theme.PRIMARY, name='출구 온도')
                
                data_flow = self.data_service.get_timeseries_groundpipe(selected_gp, hours=1, field='flow')
                if data_flow:
                    if f'{selected_gp}_flow' in self.groundpipe_chart.plot_lines:
                        self.groundpipe_chart.update_line(f'{selected_gp}_flow', data_flow)
                    else:
                        self.groundpipe_chart.add_line(f'{selected_gp}_flow', data_flow, color=Theme.WARNING, name='유량', width=1)
                
                # 로그 추가
                timeseries = self.data_service.get_timeseries_groundpipe(selected_gp, hours=1, field='t_in')
                if timeseries and len(timeseries) > 0:
                    latest_timestamp = timeseries[-1]['timestamp']
                    last_logged = self.last_log_timestamps.get(f'GP_{selected_gp}')
                    
                    if last_logged is None or latest_timestamp > last_logged:
                        data = {
                            'input_temp': stats_in['latest'],
                            'output_temp': stats_out['latest'],
                            'flow': stats_flow['latest']
                        }
                        self.log_viewer.add_sensor_data_log(latest_timestamp, 'GP', selected_gp, data)
                        self.last_log_timestamps[f'GP_{selected_gp}'] = latest_timestamp
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 전력량계 데이터 갱신 (기존 코드 유지)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            power_devices = self.data_service.get_all_power_devices()
            
            for i, card in enumerate(self.power_cards):
                if i < len(power_devices):
                    device_id = power_devices[i]
                    stats = self.data_service.get_statistics_power(device_id, hours=1)
                    card.update_value(f"{stats['latest']:.2f} kWh")
                    
                    timeseries = self.data_service.get_timeseries_power(device_id, hours=1)
                    if timeseries and len(timeseries) > 0:
                        latest_timestamp = timeseries[-1]['timestamp']
                        latest_value = timeseries[-1]['value']
                        
                        last_logged = self.last_log_timestamps.get(f'ELEC_{device_id}')
                        
                        if last_logged is None or latest_timestamp > last_logged:
                            data = {
                                'total_energy': latest_value
                            }
                            self.log_viewer.add_sensor_data_log(latest_timestamp, 'ELEC', device_id, data)
                            self.last_log_timestamps[f'ELEC_{device_id}'] = latest_timestamp
            
            for device_id in power_devices[:4]:
                data = self.data_service.get_timeseries_power(device_id, hours=1)
                if data:
                    if device_id in self.power_chart.plot_lines:
                        self.power_chart.update_line(device_id, data)
                    else:
                        self.power_chart.add_line(device_id, data, name=f'{device_id} 전력량')
            
            # 요약 카드 갱신
            self.hp_summary_card.update_value(f"{len(hp_devices)}개")
            self.gp_summary_card.update_value(f"{len(gp_devices)}개")
            self.power_summary_card.update_value(f"{len(power_devices)}개")

            # COP 탭 갱신 (현재 COP 탭이 선택된 경우에만 갱신하여 성능 절약)
            if self.tabs.currentWidget() is self.cop_tab:
                self.cop_tab.refresh()
            
            # 상태 업데이트
            self.status_label.setText('● 연결됨')
            self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
        
        except Exception as e:
            logger.error(f"데이터 갱신 오류: {e}", exc_info=True)
            self.status_label.setText('● 연결 끊김')
            self.status_label.setStyleSheet(f'color: {Theme.SECONDARY};')



    
    def open_ip_config(self):
        """플라스틱 함 IP 설정 다이얼로그 열기"""
        dialog = IPConfigDialog(self)
        dialog.exec()
    
    def open_power_config(self):
        """전력량계 설정 다이얼로그 열기"""
        dialog = PowerMeterConfigDialog(self)
        dialog.exec()
    
    def open_csv_export(self):
        """CSV 내보내기 다이얼로그 열기"""
        dialog = CSVExportDialog(self)
        dialog.exec()
    
    def show_about(self):
        """프로그램 정보 표시"""
        QMessageBox.about(
            self,
            '프로그램 정보',
            '<h2>여주 센서 모니터링 시스템</h2>'
            '<p>버전: 1.0</p>'
            '<p>개발: Soluwins</p>'
            '<p>설명: 히트펌프, 지중배관, 전력량계 실시간 모니터링</p>'
        )
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        reply = QMessageBox.question(
            self,
            '종료 확인',
            '프로그램을 종료하시겠습니까?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.timer.stop()
            logger.info("MainWindow 종료")
            event.accept()
        else:
            event.ignore()
            
    def open_layout_map(self):
        dialog = LayoutMapDialog(self)
        dialog.exec()


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="DEBUG")
    
    # 데이터베이스 연결
    initialize_connection_pool()
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())