# ==============================================
# 메인 윈도우 (대시보드 개편 버전)
# ==============================================
import threading
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QMessageBox,
    QGridLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QBrush, QFont

from ui.theme import Theme
from ui.widgets.sensor_card import SensorCard
from ui.widgets.chart_widget import ChartWidget
from ui.widgets.log_viewer_widget import LogViewerWidget
from ui.widgets.cop_tab_widget import CopTabWidget
from ui.widgets.gauge_widget import GaugeGroup
from ui.dialogs.layout_map_dialog import LayoutMapDialog
from ui.dialogs import IPConfigDialog, PowerMeterConfigDialog, CSVExportDialog
from services.ui_data_service import UIDataService
from core.database import get_queue_count
from core.modbus_tcp_manager import ModbusTcpManager
from services.alarm_service import AlarmService

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 요약 카드 (대시보드용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SummaryCard(QFrame):
    def __init__(self, icon: str, title: str, value: str, sub: str = '',
                 color: str = None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        color = color or Theme.PRIMARY
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-left: 5px solid {color};
                border-radius: 10px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(90)

        lay = QVBoxLayout()
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(4)

        # 상단: 아이콘 + 제목
        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(Theme.font(16))
        icon_lbl.setStyleSheet('border: none;')
        top.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setFont(Theme.font(10))
        title_lbl.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; border: none;')
        top.addWidget(title_lbl)
        top.addStretch()
        lay.addLayout(top)

        # 값
        self._value_lbl = QLabel(value)
        self._value_lbl.setFont(Theme.font(20, bold=True))
        self._value_lbl.setStyleSheet(f'color: {color}; border: none;')
        lay.addWidget(self._value_lbl)

        # 서브
        if sub:
            self._sub_lbl = QLabel(sub)
            self._sub_lbl.setFont(Theme.font(9))
            self._sub_lbl.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; border: none;')
            lay.addWidget(self._sub_lbl)
        else:
            self._sub_lbl = None

        self.setLayout(lay)

    def update_value(self, value: str, sub: str = ''):
        self._value_lbl.setText(value)
        if self._sub_lbl and sub:
            self._sub_lbl.setText(sub)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 알림 아이템 카드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AlarmItemCard(QFrame):
    def __init__(self, level: str, message: str, timestamp: str, parent=None):
        super().__init__(parent)
        color = Theme.DANGER if level == 'error' else Theme.WARNING
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_SECONDARY};
                border-left: 4px solid {color};
                border-radius: 6px;
                margin: 2px 0;
            }}
        """)
        lay = QHBoxLayout()
        lay.setContentsMargins(10, 6, 10, 6)

        icon = QLabel('🔴' if level == 'error' else '🟡')
        icon.setFont(Theme.font(11))
        icon.setStyleSheet('border: none;')
        lay.addWidget(icon)

        msg_lbl = QLabel(message)
        msg_lbl.setFont(Theme.font(10))
        msg_lbl.setStyleSheet(f'color: {Theme.TEXT_PRIMARY}; border: none;')
        msg_lbl.setWordWrap(True)
        lay.addWidget(msg_lbl, stretch=1)

        ts_lbl = QLabel(timestamp)
        ts_lbl.setFont(Theme.font(9))
        ts_lbl.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; border: none;')
        lay.addWidget(ts_lbl)

        self.setLayout(lay)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 윈도우
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('여주 센서 모니터링 시스템 v1.1.0')
        self.setMinimumSize(1400, 900)

        self.data_service = UIDataService()
        self.alarm_service = AlarmService.get_instance()
        self.alarm_service.on_alarm_added = self._on_alarm_added
        self.last_log_timestamps = {}

        self._status_cache = {
            'local_db':  {'text': '🖥️ 로컬 DB  ● --',   'color': Theme.TEXT_SECONDARY},
            'remote_db': {'text': '☁️ 외부 DB  ● --',   'color': Theme.TEXT_SECONDARY},
            'sensor':    {'text': '📡 센서  ● --',        'color': Theme.TEXT_SECONDARY},
            'queue':     {'text': '📦 재전송: --건',      'color': Theme.TEXT_SECONDARY},
        }
        self._status_lock = threading.Lock()

        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._check_status_async)
        self._status_timer.start(10000)
        self._check_status_async()

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)
        self.update_data()

        logger.info("MainWindow 초기화 완료")

    # ─────────────────────────────────────────
    # UI 초기화
    # ─────────────────────────────────────────
    def init_ui(self):
        self.create_menu_bar()
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel('🏭 여주 센서 모니터링 시스템')
        title.setFont(Theme.font(20, bold=True))
        title.setStyleSheet(f'color: {Theme.PRIMARY};')
        hdr.addWidget(title)
        hdr.addStretch()
        self.status_label = QLabel('● 연결됨')
        self.status_label.setFont(Theme.font(11))
        self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
        hdr.addWidget(self.status_label)
        main_layout.addLayout(hdr)

        # 탭
        self.tabs = QTabWidget()
        self.tabs.setFont(Theme.font(11))
        self.tabs.addTab(self._create_dashboard_tab(), '📊 대시보드')
        self.tabs.addTab(self._create_heatpump_tab(), '🌡️ 히트펌프')
        self.tabs.addTab(self._create_groundpipe_tab(), '🌊 지중배관')
        self.tabs.addTab(self._create_power_tab(), '⚡ 전력량계')
        self.cop_tab = CopTabWidget(self.data_service)
        self.tabs.addTab(self.cop_tab, '📈 COP')
        main_layout.addWidget(self.tabs)

        # 하단 상태바
        status_bar = QWidget()
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border-top: 1px solid {Theme.BORDER};
            }}
        """)
        sl = QHBoxLayout(status_bar)
        sl.setContentsMargins(16, 0, 16, 0)
        sl.setSpacing(16)

        self.status_local_db = QLabel('🖥️ 로컬 DB  ● --')
        self.status_local_db.setFont(Theme.font(10))
        sl.addWidget(self.status_local_db)
        sl.addWidget(self._sep())

        self.status_remote_db = QLabel('☁️ 외부 DB  ● --')
        self.status_remote_db.setFont(Theme.font(10))
        sl.addWidget(self.status_remote_db)
        sl.addWidget(self._sep())

        self.status_sensor = QLabel('📡 센서  ● --')
        self.status_sensor.setFont(Theme.font(10))
        sl.addWidget(self.status_sensor)
        sl.addWidget(self._sep())

        self.status_queue = QLabel('📦 재전송: --건')
        self.status_queue.setFont(Theme.font(10))
        sl.addWidget(self.status_queue)
        sl.addWidget(self._sep())

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
            QPushButton:hover {{ background-color: {Theme.BG_TERTIARY}; }}
        """)
        self.alarm_btn.clicked.connect(self._show_alarm_popup)
        sl.addWidget(self.alarm_btn)

        sl.addStretch()
        self.status_updated = QLabel('')
        self.status_updated.setFont(Theme.font(9))
        self.status_updated.setStyleSheet(f'color: {Theme.TEXT_SECONDARY};')
        sl.addWidget(self.status_updated)

        main_layout.addWidget(status_bar)
        central.setLayout(main_layout)

    def _sep(self):
        lbl = QLabel('│')
        lbl.setStyleSheet(f'color: {Theme.BORDER};')
        return lbl

    # ─────────────────────────────────────────
    # 대시보드 탭 (전면 개편)
    # ─────────────────────────────────────────
    def _create_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ── 1행: 요약 카드 4개 ──
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        self.card_total_devices = SummaryCard('🔌', '총 장치 수', '0', color=Theme.PRIMARY)
        self.card_online = SummaryCard('🟢', '온라인 장치', '0', color=Theme.SUCCESS)
        self.card_alarms = SummaryCard('🔔', '활성 알림', '0', color=Theme.WARNING)
        self.card_system = SummaryCard('⚙️', '시스템 상태', '정상', color=Theme.SUCCESS)
        for c in [self.card_total_devices, self.card_online, self.card_alarms, self.card_system]:
            summary_row.addWidget(c)
        layout.addLayout(summary_row)

        # ── 2행: 좌(차트+게이지) / 우(알림+장치테이블) ──
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        # 좌측
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # 온도 추이 차트
        self.dash_chart = ChartWidget('온도 센서 데이터 추이')
        self.dash_chart.set_labels(y_label='°C')
        self.dash_chart.setMinimumHeight(280)
        left_col.addWidget(self.dash_chart)

        # 게이지 그룹
        self.gauge_group = GaugeGroup('주요 센서 상태')
        left_col.addWidget(self.gauge_group)

        left_widget = QWidget()
        left_widget.setLayout(left_col)
        content_row.addWidget(left_widget, stretch=3)

        # 우측
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # 최근 알림 패널
        alarm_panel = QFrame()
        alarm_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
            }}
        """)
        alarm_panel.setFixedHeight(220)
        ap_layout = QVBoxLayout(alarm_panel)
        ap_layout.setContentsMargins(12, 10, 12, 10)
        ap_layout.setSpacing(6)

        alarm_hdr = QHBoxLayout()
        alarm_title = QLabel('🔔 최근 알림')
        alarm_title.setFont(Theme.font(11, bold=True))
        alarm_title.setStyleSheet(f'color: {Theme.TEXT_PRIMARY}; border: none;')
        alarm_hdr.addWidget(alarm_title)
        alarm_hdr.addStretch()
        all_alarm_btn = QPushButton('모두 보기')
        all_alarm_btn.setFont(Theme.font(9))
        all_alarm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Theme.PRIMARY};
                border: none;
                padding: 0;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        all_alarm_btn.clicked.connect(self._show_alarm_popup)
        alarm_hdr.addWidget(all_alarm_btn)
        ap_layout.addLayout(alarm_hdr)

        # 알림 스크롤
        self.alarm_scroll = QScrollArea()
        self.alarm_scroll.setWidgetResizable(True)
        self.alarm_scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }')
        self.alarm_container = QWidget()
        self.alarm_container.setStyleSheet('background: transparent;')
        self.alarm_container_layout = QVBoxLayout(self.alarm_container)
        self.alarm_container_layout.setContentsMargins(0, 0, 0, 0)
        self.alarm_container_layout.setSpacing(4)
        self.alarm_container_layout.addStretch()
        self.alarm_scroll.setWidget(self.alarm_container)
        ap_layout.addWidget(self.alarm_scroll)
        right_col.addWidget(alarm_panel)

        # 장치 상태 테이블
        device_panel = QFrame()
        device_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
            }}
        """)
        dp_layout = QVBoxLayout(device_panel)
        dp_layout.setContentsMargins(12, 10, 12, 10)
        dp_layout.setSpacing(6)

        dp_title = QLabel('📋 장치 상태')
        dp_title.setFont(Theme.font(11, bold=True))
        dp_title.setStyleSheet(f'color: {Theme.TEXT_PRIMARY}; border: none;')
        dp_layout.addWidget(dp_title)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(5)
        self.device_table.setHorizontalHeaderLabels(['장치명', '타입', '상태', '최신값', '마지막 수집'])
        self.device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.device_table.setAlternatingRowColors(True)
        self.device_table.setShowGrid(False)
        self.device_table.verticalHeader().setVisible(False)
        self.device_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: none;
                border-radius: 6px;
                gridline-color: {Theme.DIVIDER};
            }}
            QTableWidget::item {{
                padding: 6px 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {Theme.BG_TERTIARY};
                color: {Theme.TEXT_PRIMARY};
            }}
            QTableWidget::item:alternate {{
                background-color: {Theme.BG_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Theme.BG_PRIMARY};
                color: {Theme.TEXT_SECONDARY};
                border: none;
                border-bottom: 2px solid {Theme.PRIMARY};
                padding: 6px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        hdr = self.device_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        dp_layout.addWidget(self.device_table)
        right_col.addWidget(device_panel, stretch=1)

        right_widget = QWidget()
        right_widget.setLayout(right_col)
        right_widget.setFixedWidth(400)
        content_row.addWidget(right_widget, stretch=2)

        layout.addLayout(content_row)
        widget.setLayout(layout)
        return widget

    # ─────────────────────────────────────────
    # 히트펌프 탭
    # ─────────────────────────────────────────
    def _create_heatpump_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        ctrl = QHBoxLayout()
        device_label = QLabel('장치 선택:')
        device_label.setFont(Theme.font(12, bold=True))
        ctrl.addWidget(device_label)
        self.hp_device_combo = QComboBox()
        self.hp_device_combo.setFont(Theme.font(11))
        self.hp_device_combo.setMinimumWidth(200)
        self.hp_device_combo.currentTextChanged.connect(self.on_hp_device_changed)
        ctrl.addWidget(self.hp_device_combo)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.hp_card_in = SensorCard('입구 온도', '0.0°C', Theme.HEATPUMP_COLOR)
        self.hp_card_out = SensorCard('출구 온도', '0.0°C', Theme.PRIMARY)
        self.hp_card_flow = SensorCard('유량', '0.0 L', Theme.WARNING)
        cards.addWidget(self.hp_card_in)
        cards.addWidget(self.hp_card_out)
        cards.addWidget(self.hp_card_flow)
        layout.addLayout(cards)

        self.heatpump_chart = ChartWidget('히트펌프 온도/유량 추이')
        self.heatpump_chart.set_labels(y_label='값')
        self.heatpump_chart.time_range_changed.connect(self._on_hp_period_changed)
        layout.addWidget(self.heatpump_chart, stretch=1)

        widget.setLayout(layout)
        return widget

    # ─────────────────────────────────────────
    # 지중배관 탭
    # ─────────────────────────────────────────
    def _create_groundpipe_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        ctrl = QHBoxLayout()
        device_label = QLabel('장치 선택:')
        device_label.setFont(Theme.font(12, bold=True))
        ctrl.addWidget(device_label)
        self.gp_device_combo = QComboBox()
        self.gp_device_combo.setFont(Theme.font(11))
        self.gp_device_combo.setMinimumWidth(200)
        self.gp_device_combo.currentTextChanged.connect(self.on_gp_device_changed)
        ctrl.addWidget(self.gp_device_combo)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.gp_card_in = SensorCard('입구 온도', '0.0°C', Theme.PIPE_COLOR)
        self.gp_card_out = SensorCard('출구 온도', '0.0°C', Theme.PRIMARY)
        self.gp_card_flow = SensorCard('유량', '0.0 L', Theme.WARNING)
        cards.addWidget(self.gp_card_in)
        cards.addWidget(self.gp_card_out)
        cards.addWidget(self.gp_card_flow)
        layout.addLayout(cards)

        self.groundpipe_chart = ChartWidget('지중배관 온도/유량 추이')
        self.groundpipe_chart.set_labels(y_label='값')
        self.groundpipe_chart.time_range_changed.connect(self._on_gp_period_changed)
        layout.addWidget(self.groundpipe_chart, stretch=1)

        widget.setLayout(layout)
        return widget

    # ─────────────────────────────────────────
    # 전력량계 탭
    # ─────────────────────────────────────────
    def _create_power_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.power_cards = []
        cards = QHBoxLayout()
        cards.setSpacing(12)
        devices = self.data_service.get_all_power_devices()
        for device_id in devices[:4]:
            card = SensorCard(device_id, '0.0 kWh', Theme.POWER_COLOR)
            self.power_cards.append(card)
            cards.addWidget(card)
        layout.addLayout(cards)

        self.power_chart = ChartWidget('전력량 추이')
        self.power_chart.set_labels(y_label='전력량 (kWh)')
        self.power_chart.time_range_changed.connect(self._on_power_period_changed)
        layout.addWidget(self.power_chart, stretch=1)

        widget.setLayout(layout)
        return widget

    # ─────────────────────────────────────────
    # 메뉴바
    # ─────────────────────────────────────────
    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('파일')
        export_action = QAction('📥 CSV 내보내기', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.open_csv_export)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        exit_action = QAction('종료', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = menubar.addMenu('설정')
        layout_map_action = QAction('🏭 배치도', self)
        layout_map_action.triggered.connect(self.open_layout_map)
        settings_menu.addAction(layout_map_action)

        help_menu = menubar.addMenu('도움말')
        about_action = QAction('프로그램 정보', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    # ─────────────────────────────────────────
    # 기간 변환
    # ─────────────────────────────────────────
    def _period_to_hours(self, period_text: str) -> int:
        mapping = {
            '최근 1시간': 1, '최근 6시간': 6,
            '최근 24시간': 24, '최근 48시간': 48, '최근 7일': 168,
        }
        return mapping.get(period_text, 1)

    def _hp_hours(self):
        return self.heatpump_chart.current_time_range

    def _gp_hours(self):
        return self.groundpipe_chart.current_time_range

    def _pw_hours(self):
        return self.power_chart.current_time_range

    # ─────────────────────────────────────────
    # 장치 변경 핸들러
    # ─────────────────────────────────────────
    def on_hp_device_changed(self, device_id: str):
        if not device_id:
            return
        hours = self._hp_hours()
        try:
            stats_in   = self.data_service.get_statistics_heatpump(device_id, hours=hours, field='t_in')
            stats_out  = self.data_service.get_statistics_heatpump(device_id, hours=hours, field='t_out')
            stats_flow = self.data_service.get_statistics_heatpump(device_id, hours=hours, field='flow')
            self.hp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
            self.hp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
            self.hp_card_flow.update_value(f"{stats_flow['latest']:.1f} L")
            self.heatpump_chart.clear()
            for field, color, name in [
                ('t_in',  Theme.HEATPUMP_COLOR, '입구 온도'),
                ('t_out', Theme.PRIMARY,         '출구 온도'),
                ('flow',  Theme.WARNING,          '유량'),
            ]:
                data = self.data_service.get_timeseries_heatpump(device_id, hours=hours, field=field)
                if data:
                    self.heatpump_chart.add_line(f'{device_id}_{field}', data, color=color, name=name)
        except Exception as e:
            logger.error(f"히트펌프 장치 변경 오류: {e}", exc_info=True)

    def on_gp_device_changed(self, device_id: str):
        if not device_id:
            return
        hours = self._gp_hours()
        try:
            stats_in   = self.data_service.get_statistics_groundpipe(device_id, hours=hours, field='t_in')
            stats_out  = self.data_service.get_statistics_groundpipe(device_id, hours=hours, field='t_out')
            stats_flow = self.data_service.get_statistics_groundpipe(device_id, hours=hours, field='flow')
            self.gp_card_in.update_value(f"{stats_in['latest']:.1f}°C")
            self.gp_card_out.update_value(f"{stats_out['latest']:.1f}°C")
            self.gp_card_flow.update_value(f"{stats_flow['latest']:.1f} L")
            self.groundpipe_chart.clear()
            for field, color, name in [
                ('t_in',  Theme.PIPE_COLOR, '입구 온도'),
                ('t_out', Theme.PRIMARY,    '출구 온도'),
                ('flow',  Theme.WARNING,     '유량'),
            ]:
                data = self.data_service.get_timeseries_groundpipe(device_id, hours=hours, field=field)
                if data:
                    self.groundpipe_chart.add_line(f'{device_id}_{field}', data, color=color, name=name)
        except Exception as e:
            logger.error(f"지중배관 장치 변경 오류: {e}", exc_info=True)

    def _on_hp_period_changed(self, minutes: int):
        self.on_hp_device_changed(self.hp_device_combo.currentText())

    def _on_gp_period_changed(self, minutes: int):
        self.on_gp_device_changed(self.gp_device_combo.currentText())

    def _on_power_period_changed(self, minutes: int):
        hours = self.power_chart.current_time_range
        power_devices = self.data_service.get_all_power_devices()
        self.power_chart.clear()
        for device_id in power_devices[:4]:
            data = self.data_service.get_timeseries_power(device_id, hours=hours)
            if data:
                self.power_chart.add_line(device_id, data, name=f'{device_id} 전력량')

    # ─────────────────────────────────────────
    # 데이터 갱신
    # ─────────────────────────────────────────
    def update_data(self):
        try:
            hp_devices = self.data_service.get_all_heatpump_devices()
            gp_devices = self.data_service.get_all_groundpipe_devices()
            power_devices = self.data_service.get_all_power_devices()

            # ── 히트펌프 드롭다운 ──
            current_hp = [self.hp_device_combo.itemText(i) for i in range(self.hp_device_combo.count())]
            if current_hp != hp_devices:
                sel = self.hp_device_combo.currentText()
                self.hp_device_combo.blockSignals(True)
                self.hp_device_combo.clear()
                self.hp_device_combo.addItems(hp_devices)
                if sel in hp_devices:
                    self.hp_device_combo.setCurrentText(sel)
                elif hp_devices:
                    self.hp_device_combo.setCurrentIndex(0)
                self.hp_device_combo.blockSignals(False)

            selected_hp = self.hp_device_combo.currentText()
            hours_hp = self._hp_hours()
            if selected_hp:
                s_in   = self.data_service.get_statistics_heatpump(selected_hp, hours=hours_hp, field='t_in')
                s_out  = self.data_service.get_statistics_heatpump(selected_hp, hours=hours_hp, field='t_out')
                s_flow = self.data_service.get_statistics_heatpump(selected_hp, hours=hours_hp, field='flow')
                self.hp_card_in.update_value(f"{s_in['latest']:.1f}°C")
                self.hp_card_out.update_value(f"{s_out['latest']:.1f}°C")
                self.hp_card_flow.update_value(f"{s_flow['latest']:.1f} L")
                for field, color, name in [
                    ('t_in',  Theme.HEATPUMP_COLOR, '입구 온도'),
                    ('t_out', Theme.PRIMARY,         '출구 온도'),
                    ('flow',  Theme.WARNING,          '유량'),
                ]:
                    data = self.data_service.get_timeseries_heatpump(selected_hp, hours=hours_hp, field=field)
                    if data:
                        key = f'{selected_hp}_{field}'
                        if key in self.heatpump_chart.plot_lines:
                            self.heatpump_chart.update_line(key, data)
                        else:
                            self.heatpump_chart.add_line(key, data, color=color, name=name)

                # 로그
                ts_data = self.data_service.get_timeseries_heatpump(selected_hp, hours=hours_hp, field='t_in')
                if ts_data:
                    lt = ts_data[-1]['timestamp']
                    if self.last_log_timestamps.get(f'HP_{selected_hp}') != lt:
                        self.log_viewer.add_sensor_data_log(lt, 'HP', selected_hp, {
                            'input_temp': s_in['latest'], 'output_temp': s_out['latest'], 'flow': s_flow['latest']
                        })
                        self.last_log_timestamps[f'HP_{selected_hp}'] = lt

            # ── 지중배관 드롭다운 ──
            current_gp = [self.gp_device_combo.itemText(i) for i in range(self.gp_device_combo.count())]
            if current_gp != gp_devices:
                sel = self.gp_device_combo.currentText()
                self.gp_device_combo.blockSignals(True)
                self.gp_device_combo.clear()
                self.gp_device_combo.addItems(gp_devices)
                if sel in gp_devices:
                    self.gp_device_combo.setCurrentText(sel)
                elif gp_devices:
                    self.gp_device_combo.setCurrentIndex(0)
                self.gp_device_combo.blockSignals(False)

            selected_gp = self.gp_device_combo.currentText()
            hours_gp = self._gp_hours()
            if selected_gp:
                s_in   = self.data_service.get_statistics_groundpipe(selected_gp, hours=hours_gp, field='t_in')
                s_out  = self.data_service.get_statistics_groundpipe(selected_gp, hours=hours_gp, field='t_out')
                s_flow = self.data_service.get_statistics_groundpipe(selected_gp, hours=hours_gp, field='flow')
                self.gp_card_in.update_value(f"{s_in['latest']:.1f}°C")
                self.gp_card_out.update_value(f"{s_out['latest']:.1f}°C")
                self.gp_card_flow.update_value(f"{s_flow['latest']:.1f} L")
                for field, color, name in [
                    ('t_in',  Theme.PIPE_COLOR, '입구 온도'),
                    ('t_out', Theme.PRIMARY,    '출구 온도'),
                    ('flow',  Theme.WARNING,     '유량'),
                ]:
                    data = self.data_service.get_timeseries_groundpipe(selected_gp, hours=hours_gp, field=field)
                    if data:
                        key = f'{selected_gp}_{field}'
                        if key in self.groundpipe_chart.plot_lines:
                            self.groundpipe_chart.update_line(key, data)
                        else:
                            self.groundpipe_chart.add_line(key, data, color=color, name=name)

                ts_data = self.data_service.get_timeseries_groundpipe(selected_gp, hours=hours_gp, field='t_in')
                if ts_data:
                    lt = ts_data[-1]['timestamp']
                    if self.last_log_timestamps.get(f'GP_{selected_gp}') != lt:
                        self.log_viewer.add_sensor_data_log(lt, 'GP', selected_gp, {
                            'input_temp': s_in['latest'], 'output_temp': s_out['latest'], 'flow': s_flow['latest']
                        })
                        self.last_log_timestamps[f'GP_{selected_gp}'] = lt

            # ── 전력량계 ──
            hours_pw = self._pw_hours()
            for i, card in enumerate(self.power_cards):
                if i < len(power_devices):
                    device_id = power_devices[i]
                    stats = self.data_service.get_statistics_power(device_id, hours=hours_pw)
                    card.update_value(f"{stats['latest']:.2f} kWh")
                    ts_data = self.data_service.get_timeseries_power(device_id, hours=hours_pw)
                    if ts_data:
                        lt = ts_data[-1]['timestamp']
                        if self.last_log_timestamps.get(f'ELEC_{device_id}') != lt:
                            self.log_viewer.add_sensor_data_log(lt, 'ELEC', device_id, {'total_energy': ts_data[-1]['value']})
                            self.last_log_timestamps[f'ELEC_{device_id}'] = lt

            for device_id in power_devices[:4]:
                data = self.data_service.get_timeseries_power(device_id, hours=hours_pw)
                if data:
                    if device_id in self.power_chart.plot_lines:
                        self.power_chart.update_line(device_id, data)
                    else:
                        self.power_chart.add_line(device_id, data, name=f'{device_id} 전력량')

            # ── COP ──
            if self.tabs.currentWidget() is self.cop_tab:
                self.cop_tab.refresh()

            # ── 대시보드 갱신 ──
            self._update_dashboard(hp_devices, gp_devices, power_devices)

            # ── 상태 ──
            self.status_label.setText('● 연결됨')
            self.status_label.setStyleSheet(f'color: {Theme.SUCCESS};')
            self._apply_status_cache()
            self._update_alarm_button()

        except Exception as e:
            logger.error(f"데이터 갱신 오류: {e}", exc_info=True)
            self.status_label.setText('● 연결 끊김')
            self.status_label.setStyleSheet(f'color: {Theme.DANGER};')
            self.status_local_db.setText('🖥️ 로컬 DB  ● 연결 끊김')
            self.status_local_db.setStyleSheet(f'color: {Theme.DANGER};')

    # ─────────────────────────────────────────
    # 대시보드 갱신
    # ─────────────────────────────────────────
    def _update_dashboard(self, hp_devices, gp_devices, power_devices):
        # config 파일 기준 전체 장치 목록
        from services.config_service import ConfigService
        config_svc = ConfigService()
        all_hp = [d['device_id'] for d in config_svc.get_heatpump_ips()]
        all_gp = [d['device_id'] for d in config_svc.get_groundpipe_ips()]

        all_pm = [m['device_id'] for m in config_svc.get_all_power_meter_devices()]
        total  = len(all_hp) + len(all_gp) + len(all_pm)
        online = len(hp_devices) + len(gp_devices) + len(power_devices)
        alarm_count = self.alarm_service.count()

        # 요약 카드
        self.card_total_devices.update_value(str(total),
            f'히트펌프 {len(all_hp)} | 지중배관 {len(all_gp)} | 전력량계 {len(all_pm)}')
        self.card_online.update_value(str(online), f'오프라인 {total - online}개')
        self.card_alarms.update_value(str(alarm_count))
        sys_status = '정상' if alarm_count == 0 else f'알림 {alarm_count}건'
        self.card_system.update_value(sys_status)

        # 대시보드 차트 — 온라인 히트펌프 입구온도 표시
        for device_id in hp_devices[:4]:
            data = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='t_in')
            if data:
                key = f'dash_{device_id}'
                if key in self.dash_chart.plot_lines:
                    self.dash_chart.update_line(key, data)
                else:
                    self.dash_chart.add_line(key, data, name=f'{device_id} 입구온도')

        # 게이지 — 첫 번째 온라인 히트펌프 기준
        gauge_dev = hp_devices[0] if hp_devices else (all_hp[0] if all_hp else None)
        if gauge_dev:
            if not self.gauge_group.gauges:
                self.gauge_group.add_gauge('hp1_in',   f'{gauge_dev} 입구온도', '°C', 0, 50, Theme.HEATPUMP_COLOR)
                self.gauge_group.add_gauge('hp1_out',  f'{gauge_dev} 출구온도', '°C', 0, 50, Theme.PRIMARY)
                self.gauge_group.add_gauge('hp1_flow', f'{gauge_dev} 유량',     'L',  0, 100, Theme.WARNING)
            if gauge_dev in hp_devices:
                s_in   = self.data_service.get_statistics_heatpump(gauge_dev, hours=1, field='t_in')
                s_out  = self.data_service.get_statistics_heatpump(gauge_dev, hours=1, field='t_out')
                s_flow = self.data_service.get_statistics_heatpump(gauge_dev, hours=1, field='flow')
                self.gauge_group.update_gauge('hp1_in',   s_in['latest'])
                self.gauge_group.update_gauge('hp1_out',  s_out['latest'])
                self.gauge_group.update_gauge('hp1_flow', s_flow['latest'])

        # 알림 패널 갱신
        self._refresh_alarm_panel()

        # 장치 테이블 — config 기준 전체 장치
        self._refresh_device_table(all_hp, all_gp, all_pm, hp_devices, gp_devices, power_devices)

    def _refresh_alarm_panel(self):
        # 기존 알림 카드 제거
        while self.alarm_container_layout.count() > 1:
            item = self.alarm_container_layout.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        alarms = self.alarm_service.get_all()[:5]  # 최근 5건
        if not alarms:
            no_alarm = QLabel('✅ 현재 알림이 없습니다.')
            no_alarm.setFont(Theme.font(10))
            no_alarm.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; border: none;')
            no_alarm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.alarm_container_layout.insertWidget(0, no_alarm)
        else:
            for alarm in reversed(alarms):
                ts = alarm.timestamp.strftime('%H:%M')
                card = AlarmItemCard(alarm.level, alarm.message, ts)
                self.alarm_container_layout.insertWidget(0, card)

    def _refresh_device_table(self, all_hp, all_gp, all_pm, online_hp, online_gp, online_pm):
        """config 기준 전체 장치 표시, DB 데이터 있으면 온라인"""
        rows = []

        for dev in all_hp:
            is_online = dev in online_hp
            if is_online:
                s = self.data_service.get_statistics_heatpump(dev, hours=1, field='t_in')
                val = f"{s['latest']:.1f}°C"
            else:
                val = 'N/A'
            status = '🟢 온라인' if is_online else '⚫ 오프라인'
            rows.append((dev, '히트펌프', status, val))

        for dev in all_gp:
            is_online = dev in online_gp
            if is_online:
                s = self.data_service.get_statistics_groundpipe(dev, hours=1, field='t_in')
                val = f"{s['latest']:.1f}°C"
            else:
                val = 'N/A'
            status = '🟢 온라인' if is_online else '⚫ 오프라인'
            rows.append((dev, '지중배관', status, val))

        for dev in all_pm:
            is_online = dev in online_pm
            if is_online:
                s = self.data_service.get_statistics_power(dev, hours=1)
                val = f"{s['latest']:.2f} kWh"
            else:
                val = 'N/A'
            status = '🟢 온라인' if is_online else '⚫ 오프라인'
            rows.append((dev, '전력량계', status, val))

        self.device_table.setRowCount(len(rows))
        for r, (dev, dtype, status, val) in enumerate(rows):
            self.device_table.setItem(r, 0, QTableWidgetItem(dev))
            type_item = QTableWidgetItem(dtype)
            if dtype == '히트펌프':
                type_item.setForeground(QBrush(QColor(Theme.HEATPUMP_COLOR)))
            elif dtype == '지중배관':
                type_item.setForeground(QBrush(QColor(Theme.PIPE_COLOR)))
            else:
                type_item.setForeground(QBrush(QColor(Theme.POWER_COLOR)))
            self.device_table.setItem(r, 1, type_item)
            self.device_table.setItem(r, 2, QTableWidgetItem(status))
            self.device_table.setItem(r, 3, QTableWidgetItem(val))
            self.device_table.setItem(r, 4, QTableWidgetItem('-'))
        self.device_table.resizeRowsToContents()

    # ─────────────────────────────────────────
    # 로그 뷰어 (대시보드 내 포함 → 별도 속성)
    # ─────────────────────────────────────────
    @property
    def log_viewer(self):
        if not hasattr(self, '_log_viewer'):
            self._log_viewer = LogViewerWidget('실시간 센서 로그')
        return self._log_viewer

    # ─────────────────────────────────────────
    # 상태 체크 (백그라운드)
    # ─────────────────────────────────────────
    def _check_status_async(self):
        threading.Thread(target=self._check_status_worker, daemon=True, name="StatusChecker").start()

    def _check_status_worker(self):
        import psycopg2
        from core.config import get_config
        new_cache = {}

        # 로컬 DB
        try:
            from core.database import test_db_connection
            ok = test_db_connection()
            new_cache['local_db'] = {
                'text':  f'🖥️ 로컬 DB  ● {"정상" if ok else "연결 끊김"}',
                'color': Theme.SUCCESS if ok else Theme.DANGER
            }
        except Exception:
            new_cache['local_db'] = {'text': '🖥️ 로컬 DB  ● 연결 끊김', 'color': Theme.DANGER}

        # 외부 DB
        config = get_config()
        if not config.db_remote_enabled:
            new_cache['remote_db'] = {'text': '☁️ 외부 DB  ● 비활성', 'color': Theme.TEXT_SECONDARY}
        else:
            try:
                conn = psycopg2.connect(
                    host=config.db_remote_host, port=config.db_remote_port,
                    database=config.db_remote_name, user=config.db_remote_user,
                    password=config.db_remote_password, connect_timeout=3
                )
                conn.close()
                new_cache['remote_db'] = {'text': '☁️ 외부 DB  ● 정상', 'color': Theme.SUCCESS}
            except Exception:
                new_cache['remote_db'] = {'text': '☁️ 외부 DB  ● 연결 끊김', 'color': Theme.DANGER}

        if config.db_remote_enabled:
            AlarmService.get_instance().check_remote_db(
                new_cache['remote_db']['color'] == Theme.SUCCESS
            )

        # 센서
        try:
            manager = ModbusTcpManager.get_instance()
            connected = sum(1 for c in manager.clients.values() if c.connected)
            total = len(manager.clients)
            if total == 0:
                new_cache['sensor'] = {'text': '📡 센서  ● 대기중', 'color': Theme.TEXT_SECONDARY}
            elif connected == total:
                new_cache['sensor'] = {'text': f'📡 센서  ● 정상 ({connected}/{total})', 'color': Theme.SUCCESS}
            elif connected > 0:
                new_cache['sensor'] = {'text': f'📡 센서  ● 일부 오류 ({connected}/{total})', 'color': Theme.WARNING}
            else:
                new_cache['sensor'] = {'text': f'📡 센서  ● 전체 오류 ({connected}/{total})', 'color': Theme.DANGER}
        except Exception:
            new_cache['sensor'] = {'text': '📡 센서  ● 확인 불가', 'color': Theme.DANGER}

        # 큐
        try:
            from core.database import get_queue_count
            count = get_queue_count()
            color = Theme.SUCCESS if count == 0 else (Theme.WARNING if count < 50 else Theme.DANGER)
            new_cache['queue'] = {'text': f'📦 재전송: {count}건', 'color': color}
            AlarmService.get_instance().check_queue_size(count)
        except Exception:
            new_cache['queue'] = {'text': '📦 재전송: 확인 불가', 'color': Theme.DANGER}

        with self._status_lock:
            self._status_cache = new_cache

    def _apply_status_cache(self):
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
        self.status_updated.setText(f'갱신: {datetime.now().strftime("%H:%M:%S")}')

    # ─────────────────────────────────────────
    # 알림
    # ─────────────────────────────────────────
    def _on_alarm_added(self, alarm_item):
        QTimer.singleShot(0, self._update_alarm_button)

    def _update_alarm_button(self):
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
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox
        alarms = self.alarm_service.get_all()
        dlg = QDialog(self)
        dlg.setWindowTitle('🔔 알림 목록')
        dlg.setMinimumWidth(500)
        dlg.setMinimumHeight(350)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        count_label = QLabel(f'현재 알림 {len(alarms)}건' if alarms else '현재 알림이 없습니다.')
        count_label.setFont(Theme.font(11, bold=True))
        layout.addWidget(count_label)
        list_widget = QListWidget()
        list_widget.setFont(Theme.font(10))
        list_widget.setSpacing(2)
        for alarm in alarms:
            item = QListWidgetItem(str(alarm))
            item.setForeground(QBrush(QColor(Theme.DANGER if alarm.level == 'error' else Theme.WARNING)))
            list_widget.addItem(item)
        layout.addWidget(list_widget)
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

    # ─────────────────────────────────────────
    # 기타 메서드
    # ─────────────────────────────────────────
    def open_csv_export(self):
        CSVExportDialog(self).exec()

    def open_layout_map(self):
        LayoutMapDialog(self).exec()

    def show_about(self):
        QMessageBox.about(self, '프로그램 정보',
            '<h2>여주 센서 모니터링 시스템</h2>'
            '<p>버전: 1.1.0</p><p>개발: Soluwins</p>'
            '<p>히트펌프, 지중배관, 전력량계 실시간 모니터링</p>')

    def closeEvent(self, event):
        reply = QMessageBox.question(self, '종료 확인', '프로그램을 종료하시겠습니까?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.timer.stop()
            self._status_timer.stop()
            logger.info("MainWindow 종료")
            event.accept()
        else:
            event.ignore()
