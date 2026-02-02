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
    QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from ui.theme import Theme
from ui.widgets.sensor_card import SensorCard
from ui.widgets.chart_widget import ChartWidget
from ui.widgets.log_viewer_widget import LogViewerWidget
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
        
        # 플라스틱 함 IP 설정
        ip_config_action = QAction('🌡️ 플라스틱 함 IP 설정', self)
        ip_config_action.triggered.connect(self.open_ip_config)
        settings_menu.addAction(ip_config_action)
        
        # 전력량계 설정
        power_config_action = QAction('⚡ 전력량계 설정', self)
        power_config_action.triggered.connect(self.open_power_config)
        settings_menu.addAction(power_config_action)
        
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
        
        # 센서 카드
        self.heatpump_cards = []
        cards_layout = QHBoxLayout()
        
        # 히트펌프 장치 목록 가져오기
        devices = self.data_service.get_all_heatpump_devices()
        
        for device_id in devices[:4]:  # 최대 4개
            card = SensorCard(device_id, '0.0°C', Theme.HEATPUMP_COLOR)
            self.heatpump_cards.append(card)
            cards_layout.addWidget(card)
        
        layout.addLayout(cards_layout)
        
        # 차트
        self.heatpump_chart = ChartWidget('히트펌프 온도 추이')
        self.heatpump_chart.set_labels(y_label='온도 (°C)')
        layout.addWidget(self.heatpump_chart)
        
        widget.setLayout(layout)
        return widget
    
    def create_groundpipe_tab(self):
        """지중배관 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 센서 카드
        self.groundpipe_cards = []
        cards_layout = QHBoxLayout()
        
        # 지중배관 장치 목록 가져오기
        devices = self.data_service.get_all_groundpipe_devices()
        
        for device_id in devices[:4]:  # 최대 4개
            card = SensorCard(device_id, '0.0°C', Theme.PIPE_COLOR)
            self.groundpipe_cards.append(card)
            cards_layout.addWidget(card)
        
        layout.addLayout(cards_layout)
        
        # 차트
        self.groundpipe_chart = ChartWidget('지중배관 온도 추이')
        self.groundpipe_chart.set_labels(y_label='온도 (°C)')
        layout.addWidget(self.groundpipe_chart)
        
        widget.setLayout(layout)
        return widget
    
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
            
            # 카드 업데이트
            for i, card in enumerate(self.heatpump_cards):
                if i < len(hp_devices):
                    device_id = hp_devices[i]
                    stats = self.data_service.get_statistics_heatpump(device_id, hours=1, field='t_in')
                    card.update_value(f"{stats['latest']}°C")
                    
                    # ✅ 새로운 데이터가 있을 때만 로그 추가
                    timeseries = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='t_in')
                    if timeseries and len(timeseries) > 0:
                        latest_timestamp = timeseries[-1]['timestamp']
                        
                        last_logged = self.last_log_timestamps.get(f'HP_{device_id}')
                        
                        if last_logged is None or latest_timestamp > last_logged:
                            # ✅✅ 입구/출구 온도 각각 조회
                            stats_in = self.data_service.get_statistics_heatpump(device_id, hours=1, field='t_in')
                            stats_out = self.data_service.get_statistics_heatpump(device_id, hours=1, field='t_out')
                            stats_flow = self.data_service.get_statistics_heatpump(device_id, hours=1, field='flow')
                            
                            data = {
                                'input_temp': stats_in['latest'],
                                'output_temp': stats_out['latest'],
                                'flow': stats_flow['latest']
                            }
                            self.log_viewer.add_sensor_data_log(latest_timestamp, 'HP', device_id, data)
                            self.last_log_timestamps[f'HP_{device_id}'] = latest_timestamp
            
            # 차트 업데이트
            for device_id in hp_devices[:4]:
                # 입구 온도
                data_in = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='t_in')
                if data_in:
                    self.heatpump_chart.add_line(
                        f'{device_id}_in',
                        data_in,
                        color=Theme.HEATPUMP_COLOR,
                        name=f'{device_id} 입구'
                    )
                
                # 출구 온도
                data_out = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='t_out')
                if data_out:
                    self.heatpump_chart.add_line(
                        f'{device_id}_out',
                        data_out,
                        color=Theme.PRIMARY,
                        name=f'{device_id} 출구'
                    )
                
                # 유량 (선택사항 - 스케일이 다를 수 있음)
                data_flow = self.data_service.get_timeseries_heatpump(device_id, hours=1, field='flow')
                if data_flow:
                    self.heatpump_chart.add_line(
                        f'{device_id}_flow',
                        data_flow,
                        color=Theme.WARNING,
                        name=f'{device_id} 유량',
                        width=1
                    )
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 지중배관 데이터 갱신
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            gp_devices = self.data_service.get_all_groundpipe_devices()
            
            # 카드 업데이트
            for i, card in enumerate(self.groundpipe_cards):
                if i < len(gp_devices):
                    device_id = gp_devices[i]
                    stats = self.data_service.get_statistics_groundpipe(device_id, hours=1, field='t_in')
                    card.update_value(f"{stats['latest']}°C")
                    
                    # ✅ 새로운 데이터가 있을 때만 로그 추가
                    timeseries = self.data_service.get_timeseries_groundpipe(device_id, hours=1, field='t_in')
                    if timeseries and len(timeseries) > 0:
                        latest_timestamp = timeseries[-1]['timestamp']
                        
                        last_logged = self.last_log_timestamps.get(f'GP_{device_id}')
                        
                        if last_logged is None or latest_timestamp > last_logged:
                            # ✅✅ 입구/출구 온도 각각 조회
                            stats_in = self.data_service.get_statistics_groundpipe(device_id, hours=1, field='t_in')
                            stats_out = self.data_service.get_statistics_groundpipe(device_id, hours=1, field='t_out')
                            stats_flow = self.data_service.get_statistics_groundpipe(device_id, hours=1, field='flow')
                            
                            data = {
                                'input_temp': stats_in['latest'],
                                'output_temp': stats_out['latest'],
                                'flow': stats_flow['latest']
                            }
                            self.log_viewer.add_sensor_data_log(latest_timestamp, 'GP', device_id, data)
                            self.last_log_timestamps[f'GP_{device_id}'] = latest_timestamp
            
            # 차트 업데이트
            for device_id in gp_devices[:4]:
                # 입구 온도
                data_in = self.data_service.get_timeseries_groundpipe(device_id, hours=1, field='t_in')
                if data_in:
                    self.groundpipe_chart.add_line(
                        f'{device_id}_in',
                        data_in,
                        color=Theme.PIPE_COLOR,
                        name=f'{device_id} 입구'
                    )
                
                # 출구 온도
                data_out = self.data_service.get_timeseries_groundpipe(device_id, hours=1, field='t_out')
                if data_out:
                    self.groundpipe_chart.add_line(
                        f'{device_id}_out',
                        data_out,
                        color=Theme.PRIMARY,
                        name=f'{device_id} 출구'
                    )
                
                # 유량
                data_flow = self.data_service.get_timeseries_groundpipe(device_id, hours=1, field='flow')
                if data_flow:
                    self.groundpipe_chart.add_line(
                        f'{device_id}_flow',
                        data_flow,
                        color=Theme.WARNING,
                        name=f'{device_id} 유량',
                        width=1
                    )
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 전력량계 데이터 갱신
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            power_devices = self.data_service.get_all_power_devices()
            
            # 카드 업데이트
            for i, card in enumerate(self.power_cards):
                if i < len(power_devices):
                    device_id = power_devices[i]
                    stats = self.data_service.get_statistics_power(device_id, hours=1)
                    
                    # ✅✅ 카드 값 확인 (디버깅)
                    logger.debug(f"[전력량계 카드] {device_id}: {stats['latest']} kWh")
                    card.update_value(f"{stats['latest']} kWh")
                    
                    # ✅ 새로운 데이터가 있을 때만 로그 추가
                    timeseries = self.data_service.get_timeseries_power(device_id, hours=1)
                    if timeseries and len(timeseries) > 0:
                        latest_timestamp = timeseries[-1]['timestamp']
                        latest_value = timeseries[-1]['value']
                        
                        # ✅✅ 로그 값 확인 (디버깅)
                        logger.debug(f"[전력량계 로그] {device_id}: {latest_value} kWh @ {latest_timestamp}")
                        
                        last_logged = self.last_log_timestamps.get(f'ELEC_{device_id}')
                        
                        if last_logged is None or latest_timestamp > last_logged:
                            data = {
                                'total_energy': latest_value  # ✅✅ timeseries의 실제 값 사용
                            }
                            self.log_viewer.add_sensor_data_log(latest_timestamp, 'ELEC', device_id, data)
                            self.last_log_timestamps[f'ELEC_{device_id}'] = latest_timestamp
            
            # 차트 업데이트
            for device_id in power_devices[:4]:
                data = self.data_service.get_timeseries_power(device_id, hours=1)
                if data:
                    self.power_chart.add_line(device_id, data, name=f'{device_id} 전력량')
            
            # 요약 카드 갱신
            self.hp_summary_card.update_value(f"{len(hp_devices)}개")
            self.gp_summary_card.update_value(f"{len(gp_devices)}개")
            self.power_summary_card.update_value(f"{len(power_devices)}개")
            
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
            '<p>버전: 1.0.0</p>'
            '<p>개발: SoluWins</p>'
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
