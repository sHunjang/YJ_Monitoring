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

import threading
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

from core.database import get_queue_count
from core.modbus_tcp_manager import ModbusTcpManager

from services.alarm_service import AlarmService

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
        
        # 알림 서비스
        self.alarm_service = AlarmService.get_instance()
        self.alarm_service.on_alarm_added = self._on_alarm_added
        
        # 마지막 로그 타임스탬프 추적
        self.last_log_timestamps = {}   # {device_id: timestamp}
    
        # 상태 캐시 (백그라운드 스레드가 갱신)
        self._status_cache = {
            'local_db':  {'text': '🖥️ 로컬 DB  ● --',      'color': Theme.TEXT_SECONDARY},
            'remote_db': {'text': '☁️ 원격 DB  ● --',      'color': Theme.TEXT_SECONDARY},
            'sensor':    {'text': '📡 센서  ● --',           'color': Theme.TEXT_SECONDARY},
            'queue':     {'text': '📦 재전송 대기: --건',    'color': Theme.TEXT_SECONDARY},
        }
        self._status_lock = threading.Lock()

        # 상태 체크 타이머 (10초마다 백그라운드에서 체크)
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._check_status_async)
        self._status_timer.start(10000)  # 10초
        self._check_status_async()  # 최초 1회 즉시 실행
    
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
        self.create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ── 헤더 ──────────────────────────────────
        header_layout = QHBoxLayout()
        title = QLabel('🏭 여주 센서 모니터링 시스템')
        title.setFont(Theme.font(20, bold=True))
        title.setStyleSheet(f'color: {Theme.PRIMARY};')
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.status_label = QLabel('● 연결됨')
        self.status_label.setFont(Theme.font(11))
        self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
        header_layout.addWidget(self.status_label)
        main_layout.addLayout(header_layout)  # ← addLayout (Layout이라 addLayout)

        # ── 탭 위젯 ───────────────────────────────
        self.tabs = QTabWidget()                # ← tabs 먼저 생성
        self.tabs.setFont(Theme.font(11))

        dashboard_tab = self.create_dashboard_tab()
        self.tabs.addTab(dashboard_tab, '📊 대시보드')

        heatpump_tab = self.create_heatpump_tab()
        self.tabs.addTab(heatpump_tab, '🌡️ 히트펌프')

        groundpipe_tab = self.create_groundpipe_tab()
        self.tabs.addTab(groundpipe_tab, '🌊 지중배관')

        power_tab = self.create_power_tab()
        self.tabs.addTab(power_tab, '⚡ 전력량계')

        self.cop_tab = CopTabWidget(self.data_service)
        self.tabs.addTab(self.cop_tab, '📈 COP')

        main_layout.addWidget(self.tabs)        # ← tabs 생성 후 추가

        # ── 하단 상태바 ───────────────────────────
        status_bar = QWidget()
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border-top: 1px solid {Theme.BORDER};
            }}
        """)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)
        status_layout.setSpacing(20)

        self.status_local_db = QLabel('🖥️ 로컬 DB  ● --')
        self.status_local_db.setFont(Theme.font(10))
        status_layout.addWidget(self.status_local_db)

        sep1 = QLabel('│')
        sep1.setStyleSheet(f'color: {Theme.BORDER};')
        status_layout.addWidget(sep1)

        self.status_remote_db = QLabel('☁️ 원격 DB  ● --')
        self.status_remote_db.setFont(Theme.font(10))
        status_layout.addWidget(self.status_remote_db)

        sep2 = QLabel('│')
        sep2.setStyleSheet(f'color: {Theme.BORDER};')
        status_layout.addWidget(sep2)

        self.status_sensor = QLabel('📡 센서  ● --')
        self.status_sensor.setFont(Theme.font(10))
        status_layout.addWidget(self.status_sensor)

        sep3 = QLabel('│')
        sep3.setStyleSheet(f'color: {Theme.BORDER};')
        status_layout.addWidget(sep3)

        self.status_queue = QLabel('📦 재전송 대기: --건')
        self.status_queue.setFont(Theme.font(10))
        status_layout.addWidget(self.status_queue)

        # 알림 버튼
        self.alarm_btn = QPushButton('🔔 0건')
        self.alarm_btn.setFont(Theme.font(10))
        self.alarm_btn.setFixedHeight(24)
        self.alarm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {Theme.BORDER};
                border-radius: 4px;
                padding: 0 8px;
                color: {Theme.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background-color: {Theme.BG_TERTIARY};
            }}
        """)
        self.alarm_btn.clicked.connect(self._show_alarm_popup)
        status_layout.addWidget(self.alarm_btn)

        status_layout.addStretch()

        self.status_updated = QLabel('')
        self.status_updated.setFont(Theme.font(9))
        self.status_updated.setStyleSheet(f'color: {Theme.TEXT_SECONDARY};')
        status_layout.addWidget(self.status_updated)

        main_layout.addWidget(status_bar)       # ← 탭 다음에 상태바

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

        # ── 기간 선택 추가 ──────────────────────────
        period_label = QLabel('조회 기간:')
        period_label.setFont(Theme.font(11))
        control_layout.addWidget(period_label)

        self.hp_period_combo = QComboBox()
        self.hp_period_combo.setFont(Theme.font(11))
        self.hp_period_combo.addItems(['최근 1시간', '최근 6시간', '최근 24시간', '최근 48시간', '최근 7일'])
        self.hp_period_combo.currentTextChanged.connect(self.on_hp_device_changed_with_period)
        control_layout.addWidget(self.hp_period_combo)
        # ────────────────────────────────────────────

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

        # ── 기간 선택 추가 ──────────────────────────
        period_label = QLabel('조회 기간:')
        period_label.setFont(Theme.font(11))
        control_layout.addWidget(period_label)

        self.gp_period_combo = QComboBox()
        self.gp_period_combo.setFont(Theme.font(11))
        self.gp_period_combo.addItems(['최근 1시간', '최근 6시간', '최근 24시간', '최근 48시간', '최근 7일'])
        self.gp_period_combo.currentTextChanged.connect(self.on_gp_device_changed_with_period)
        control_layout.addWidget(self.gp_period_combo)
        # ────────────────────────────────────────────

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
        self.on_hp_device_changed_with_period()

    def on_hp_device_changed_with_period(self):
        """히트펌프 장치/기간 변경 시 차트 갱신"""
        device_id = self.hp_device_combo.currentText()
        if not device_id:
            return

        hours = self._period_to_hours(self.hp_period_combo.currentText())

        try:
            stats_in   = self.data_service.get_statistics_heatpump(device_id, hours=hours, field='t_in')
            stats_out  = self.data_service.get_statistics_heatpump(device_id, hours=hours, field='t_out')
            stats_flow = self.data_service.get_statistics_heatpump(device_id, hours=hours, field='flow')

            self.hp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
            self.hp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
            self.hp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")

            self.heatpump_chart.clear()

            data_in = self.data_service.get_timeseries_heatpump(device_id, hours=hours, field='t_in')
            if data_in:
                self.heatpump_chart.add_line(f'{device_id}_in', data_in,
                                            color=Theme.HEATPUMP_COLOR, name='입구 온도')

            data_out = self.data_service.get_timeseries_heatpump(device_id, hours=hours, field='t_out')
            if data_out:
                self.heatpump_chart.add_line(f'{device_id}_out', data_out,
                                            color=Theme.PRIMARY, name='출구 온도')

            data_flow = self.data_service.get_timeseries_heatpump(device_id, hours=hours, field='flow')
            if data_flow:
                self.heatpump_chart.add_line(f'{device_id}_flow', data_flow,
                                            color=Theme.WARNING, name='유량', width=1)

        except Exception as e:
            logger.error(f"히트펌프 차트 갱신 오류: {e}", exc_info=True)

    def on_gp_device_changed(self, device_id: str):
        """지중배관 장치 선택 변경"""
        self.on_gp_device_changed_with_period()

    def on_gp_device_changed_with_period(self):
        """지중배관 장치/기간 변경 시 차트 갱신"""
        device_id = self.gp_device_combo.currentText()
        if not device_id:
            return

        hours = self._period_to_hours(self.gp_period_combo.currentText())

        try:
            stats_in   = self.data_service.get_statistics_groundpipe(device_id, hours=hours, field='t_in')
            stats_out  = self.data_service.get_statistics_groundpipe(device_id, hours=hours, field='t_out')
            stats_flow = self.data_service.get_statistics_groundpipe(device_id, hours=hours, field='flow')

            self.gp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
            self.gp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
            self.gp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")

            self.groundpipe_chart.clear()

            data_in = self.data_service.get_timeseries_groundpipe(device_id, hours=hours, field='t_in')
            if data_in:
                self.groundpipe_chart.add_line(f'{device_id}_in', data_in,
                                                color=Theme.PIPE_COLOR, name='입구 온도')

            data_out = self.data_service.get_timeseries_groundpipe(device_id, hours=hours, field='t_out')
            if data_out:
                self.groundpipe_chart.add_line(f'{device_id}_out', data_out,
                                                color=Theme.PRIMARY, name='출구 온도')

            data_flow = self.data_service.get_timeseries_groundpipe(device_id, hours=hours, field='flow')
            if data_flow:
                self.groundpipe_chart.add_line(f'{device_id}_flow', data_flow,
                                                color=Theme.WARNING, name='유량', width=1)

        except Exception as e:
            logger.error(f"지중배관 차트 갱신 오류: {e}", exc_info=True)
    
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

        # ── 기간 선택 추가 ──────────────────────────
        power_control = QHBoxLayout()
        period_label = QLabel('조회 기간:')
        period_label.setFont(Theme.font(11))
        power_control.addWidget(period_label)

        self.power_period_combo = QComboBox()
        self.power_period_combo.setFont(Theme.font(11))
        self.power_period_combo.addItems(['최근 1시간', '최근 6시간', '최근 24시간', '최근 48시간', '최근 7일'])
        self.power_period_combo.currentTextChanged.connect(self._on_power_period_changed)
        power_control.addWidget(self.power_period_combo)
        power_control.addStretch()
        layout.addLayout(power_control)
        # ────────────────────────────────────────────

        # 차트
        self.power_chart = ChartWidget('전력량 추이')
        self.power_chart.set_labels(y_label='전력량 (kWh)')
        layout.addWidget(self.power_chart)
        
        widget.setLayout(layout)
        return widget

    def _on_power_period_changed(self):
        """전력량계 기간 변경 시 차트 갱신"""
        hours = self._period_to_hours(self.power_period_combo.currentText())
        power_devices = self.data_service.get_all_power_devices()

        self.power_chart.clear()

        for device_id in power_devices[:4]:
            data = self.data_service.get_timeseries_power(device_id, hours=hours)
            if data:
                self.power_chart.add_line(device_id, data, name=f'{device_id} 전력량')

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
                stats_in = self.data_service.get_statistics_heatpump(selected_hp, hours = self._period_to_hours(self.hp_period_combo.currentText()), field='t_in')
                stats_out = self.data_service.get_statistics_heatpump(selected_hp, hours = self._period_to_hours(self.hp_period_combo.currentText()), field='t_out')
                stats_flow = self.data_service.get_statistics_heatpump(selected_hp, hours = self._period_to_hours(self.hp_period_combo.currentText()), field='flow')
                
                self.hp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
                self.hp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
                self.hp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")
                
                # 차트 업데이트 (update_line 사용)
                data_in = self.data_service.get_timeseries_heatpump(selected_hp, hours = self._period_to_hours(self.hp_period_combo.currentText()), field='t_in')
                if data_in:
                    if f'{selected_hp}_in' in self.heatpump_chart.plot_lines:
                        self.heatpump_chart.update_line(f'{selected_hp}_in', data_in)
                    else:
                        self.heatpump_chart.add_line(f'{selected_hp}_in', data_in, color=Theme.HEATPUMP_COLOR, name='입구 온도')
                
                data_out = self.data_service.get_timeseries_heatpump(selected_hp, hours = self._period_to_hours(self.hp_period_combo.currentText()), field='t_out')
                if data_out:
                    if f'{selected_hp}_out' in self.heatpump_chart.plot_lines:
                        self.heatpump_chart.update_line(f'{selected_hp}_out', data_out)
                    else:
                        self.heatpump_chart.add_line(f'{selected_hp}_out', data_out, color=Theme.PRIMARY, name='출구 온도')
                
                data_flow = self.data_service.get_timeseries_heatpump(selected_hp, hours = self._period_to_hours(self.hp_period_combo.currentText()), field='flow')
                if data_flow:
                    if f'{selected_hp}_flow' in self.heatpump_chart.plot_lines:
                        self.heatpump_chart.update_line(f'{selected_hp}_flow', data_flow)
                    else:
                        self.heatpump_chart.add_line(f'{selected_hp}_flow', data_flow, color=Theme.WARNING, name='유량', width=1)
                
                # 로그 추가
                timeseries = self.data_service.get_timeseries_heatpump(selected_hp, hours = self._period_to_hours(self.hp_period_combo.currentText()), field='t_in')
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
                stats_in = self.data_service.get_statistics_groundpipe(selected_gp, hours = self._period_to_hours(self.gp_period_combo.currentText()), field='t_in')
                stats_out = self.data_service.get_statistics_groundpipe(selected_gp, hours = self._period_to_hours(self.gp_period_combo.currentText()), field='t_out')
                stats_flow = self.data_service.get_statistics_groundpipe(selected_gp, hours = self._period_to_hours(self.gp_period_combo.currentText()), field='flow')
                
                self.gp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
                self.gp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
                self.gp_card_flow.update_value(f"{stats_flow['latest']:.1f} L/min")
                
                # 차트 업데이트 (update_line 사용)
                data_in = self.data_service.get_timeseries_groundpipe(selected_gp, hours = self._period_to_hours(self.gp_period_combo.currentText()), field='t_in')
                if data_in:
                    if f'{selected_gp}_in' in self.groundpipe_chart.plot_lines:
                        self.groundpipe_chart.update_line(f'{selected_gp}_in', data_in)
                    else:
                        self.groundpipe_chart.add_line(f'{selected_gp}_in', data_in, color=Theme.PIPE_COLOR, name='입구 온도')
                
                data_out = self.data_service.get_timeseries_groundpipe(selected_gp, hours = self._period_to_hours(self.gp_period_combo.currentText()), field='t_out')
                if data_out:
                    if f'{selected_gp}_out' in self.groundpipe_chart.plot_lines:
                        self.groundpipe_chart.update_line(f'{selected_gp}_out', data_out)
                    else:
                        self.groundpipe_chart.add_line(f'{selected_gp}_out', data_out, color=Theme.PRIMARY, name='출구 온도')
                
                data_flow = self.data_service.get_timeseries_groundpipe(selected_gp, hours = self._period_to_hours(self.gp_period_combo.currentText()), field='flow')
                if data_flow:
                    if f'{selected_gp}_flow' in self.groundpipe_chart.plot_lines:
                        self.groundpipe_chart.update_line(f'{selected_gp}_flow', data_flow)
                    else:
                        self.groundpipe_chart.add_line(f'{selected_gp}_flow', data_flow, color=Theme.WARNING, name='유량', width=1)
                
                # 로그 추가
                timeseries = self.data_service.get_timeseries_groundpipe(selected_gp, hours = self._period_to_hours(self.gp_period_combo.currentText()), field='t_in')
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
                    stats = self.data_service.get_statistics_power(device_id, hours = self._period_to_hours(self.power_period_combo.currentText()))
                    card.update_value(f"{stats['latest']:.2f} kWh")
                    
                    timeseries = self.data_service.get_timeseries_power(device_id, hours = self._period_to_hours(self.power_period_combo.currentText()))
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
                data = self.data_service.get_timeseries_power(device_id, hours = self._period_to_hours(self.power_period_combo.currentText()))
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
            # ── 하단 상태바 갱신 ──────────────────────────
            self._apply_status_cache()
            self._update_alarm_button()
            
            self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
        
        except Exception as e:
            logger.error(f"데이터 갱신 오류: {e}", exc_info=True)
            self.status_label.setText('● 연결 끊김')
            self.status_label.setStyleSheet(f'color: {Theme.SECONDARY};')

            # 추가
            self.status_local_db.setText('🖥️ 로컬 DB  ● 연결 끊김')
            self.status_local_db.setStyleSheet(f'color: {Theme.DANGER};')


    def _check_status_async(self):
        """백그라운드 스레드에서 연결 상태 체크"""
        thread = threading.Thread(
            target=self._check_status_worker,
            daemon=True,
            name="StatusChecker"
        )
        thread.start()

    def _check_status_worker(self):
        """실제 상태 체크 작업 (별도 스레드에서 실행)"""
        import psycopg2
        from core.config import get_config
        from core.database import get_queue_count
        from core.modbus_tcp_manager import ModbusTcpManager

        new_cache = {}

        # ── 로컬 DB ──────────────────────────────
        try:
            from core.database import test_db_connection
            if test_db_connection():
                new_cache['local_db'] = {
                    'text':  '🖥️ 로컬 DB  ● 정상',
                    'color': Theme.SUCCESS
                }
            else:
                new_cache['local_db'] = {
                    'text':  '🖥️ 로컬 DB  ● 연결 끊김',
                    'color': Theme.DANGER
                }
        except Exception:
            new_cache['local_db'] = {
                'text':  '🖥️ 로컬 DB  ● 연결 끊김',
                'color': Theme.DANGER
            }

        # ── 원격 DB ──────────────────────────────
        config = get_config()
        if not config.db_remote_enabled:
            new_cache['remote_db'] = {
                'text':  '☁️ 원격 DB  ● 비활성',
                'color': Theme.TEXT_SECONDARY
            }
        else:
            try:
                conn = psycopg2.connect(
                    host=config.db_remote_host,
                    port=config.db_remote_port,
                    database=config.db_remote_name,
                    user=config.db_remote_user,
                    password=config.db_remote_password,
                    connect_timeout=3
                )
                conn.close()
                new_cache['remote_db'] = {
                    'text':  '☁️ 원격 DB  ● 정상',
                    'color': Theme.SUCCESS
                }
            except Exception:
                new_cache['remote_db'] = {
                    'text':  '☁️ 원격 DB  ● 연결 끊김',
                    'color': Theme.DANGER
                }

        # 원격 DB 알림 체크 추가
        from services.alarm_service import AlarmService
        AlarmService.get_instance().check_remote_db(
            new_cache['remote_db']['color'] == Theme.SUCCESS
        )

        # ── 센서 네트워크 ─────────────────────────
        try:
            manager = ModbusTcpManager.get_instance()
            connected = sum(1 for c in manager.clients.values() if c.connected)
            total = len(manager.clients)
            if total == 0:
                new_cache['sensor'] = {
                    'text':  '📡 센서  ● 대기중',
                    'color': Theme.TEXT_SECONDARY
                }
            elif connected == total:
                new_cache['sensor'] = {
                    'text':  f'📡 센서  ● 정상 ({connected}/{total})',
                    'color': Theme.SUCCESS
                }
            elif connected > 0:
                new_cache['sensor'] = {
                    'text':  f'📡 센서  ● 일부 오류 ({connected}/{total})',
                    'color': Theme.WARNING
                }
            else:
                new_cache['sensor'] = {
                    'text':  f'📡 센서  ● 전체 오류 ({connected}/{total})',
                    'color': Theme.DANGER
                }
        except Exception:
            new_cache['sensor'] = {
                'text':  '📡 센서  ● 확인 불가',
                'color': Theme.DANGER
            }

        # ── 재전송 큐 ─────────────────────────────
        try:
            count = get_queue_count()
            if count == 0:
                color = Theme.SUCCESS
            elif count < 50:
                color = Theme.WARNING
            else:
                color = Theme.DANGER
            new_cache['queue'] = {
                'text':  f'📦 재전송 대기: {count}건',
                'color': color
            }
        except Exception:
            new_cache['queue'] = {
                'text':  '📦 재전송 대기: 확인 불가',
                'color': Theme.DANGER
            }

        # ── 캐시 업데이트 ─────────────────────────
        with self._status_lock:
            self._status_cache = new_cache

    def _apply_status_cache(self):
        """캐시된 상태값을 UI에 반영 (메인 스레드에서 호출)"""
        with self._status_lock:
            cache = dict(self._status_cache)

        self.status_local_db.setText(cache['local_db']['text'])
        self.status_local_db.setStyleSheet(f"color: {cache['local_db']['color']};")

        self.status_remote_db.setText(cache['remote_db']['text'])
        self.status_remote_db.setStyleSheet(f"color: {cache['remote_db']['color']};")

        self.status_sensor.setText(cache['sensor']['text'])
        self.status_sensor.setStyleSheet(f"color: {cache['sensor']['color']};")

        self.status_queue.setText(cache['queue']['text'])
        self.status_queue.setStyleSheet(f"color: {cache['queue']['color']};")

        self.status_updated.setText(
            f'갱신: {datetime.now().strftime("%H:%M:%S")}'
        )

    
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
            self._status_timer.stop()
            logger.info("MainWindow 종료")
            event.accept()
        else:
            event.ignore()
            
    def open_layout_map(self):
        dialog = LayoutMapDialog(self)
        dialog.exec()

    def _on_alarm_added(self, alarm_item):
        """새 알림 발생 시 버튼 갱신 (백그라운드 스레드에서 호출될 수 있음)"""
        # Qt UI 업데이트는 메인 스레드에서 해야 하므로 QTimer로 지연 호출
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._update_alarm_button)

    def _update_alarm_button(self):
        """알림 버튼 텍스트/색상 갱신"""
        count = self.alarm_service.count()
        self.alarm_btn.setText(f'🔔 {count}건')

        if count == 0:
            self.alarm_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {Theme.BORDER};
                    border-radius: 4px;
                    padding: 0 8px;
                    color: {Theme.TEXT_SECONDARY};
                }}
                QPushButton:hover {{ background-color: {Theme.BG_TERTIARY}; }}
            """)
        else:
            self.alarm_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.DANGER};
                    border: none;
                    border-radius: 4px;
                    padding: 0 8px;
                    color: #ffffff;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #a93226; }}
            """)

    def _show_alarm_popup(self):
        """알림 목록 팝업"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox
        from PyQt6.QtGui import QColor

        alarms = self.alarm_service.get_all()

        dlg = QDialog(self)
        dlg.setWindowTitle('🔔 알림 목록')
        dlg.setMinimumWidth(500)
        dlg.setMinimumHeight(350)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 알림 개수 표시
        count_label = QLabel(
            f'현재 알림 {len(alarms)}건' if alarms else '현재 알림이 없습니다.'
        )
        count_label.setFont(Theme.font(11, bold=True))
        layout.addWidget(count_label)

        # 알림 목록
        list_widget = QListWidget()
        list_widget.setFont(Theme.font(10))
        list_widget.setSpacing(2)

        for alarm in alarms:
            item = QListWidgetItem(str(alarm))
            if alarm.level == 'error':
                item.setForeground(QColor(Theme.DANGER))
            else:
                item.setForeground(QColor(Theme.WARNING))
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        # 버튼
        btn_box = QDialogButtonBox()
        clear_btn = btn_box.addButton('전체 해제', QDialogButtonBox.ButtonRole.ResetRole)
        close_btn = btn_box.addButton('닫기', QDialogButtonBox.ButtonRole.AcceptRole)

        def on_clear():
            self.alarm_service.resolve_all()
            self._update_alarm_button()
            dlg.accept()

        clear_btn.clicked.connect(on_clear)
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(btn_box)

        dlg.setLayout(layout)
        dlg.exec()
        self._update_alarm_button()

    def _period_to_hours(self, period_text: str) -> int:
        """기간 텍스트를 시간(int)으로 변환"""
        mapping = {
            '최근 1시간':  1,
            '최근 6시간':  6,
            '최근 24시간': 24,
            '최근 48시간': 48,
            '최근 7일':    168,
        }
        return mapping.get(period_text, 1)

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