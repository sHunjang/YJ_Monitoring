# ==============================================
# 메인 윈도우
# ==============================================
"""
여주 센서 모니터링 GUI

기능:
- 사이드바: 센서 트리 네비게이션 + 다중 선택
- 차트: 여러 센서 동시 비교
- 데이터 내보내기: CSV/Excel
- 자동 새로고침
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QHeaderView, QTreeWidget,
    QTreeWidgetItem, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

import pyqtgraph as pg
import pandas as pd

from services.ui_data_service import UIDataService
from ui.theme import Theme

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    
    def __init__(self):
        """초기화 메서드"""
        super().__init__()
        
        # 데이터베이스 접근 서비스 초기화
        self.service = UIDataService()
        
        # .env 파일에서 데이터 수집 주기 가져오기 (기본값: 60초)
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL', 60))
        
        # UI 갱신 주기 = 데이터 수집 주기 + 3초 (DB 저장 대기 시간)
        self.ui_refresh_interval = self.collection_interval + 3
        
        # 다음 자동 갱신까지 남은 시간 추적용 변수
        self.seconds_until_refresh = self.ui_refresh_interval
        
        # 현재 선택된 센서들 저장 (센서ID: (센서타입, 측정필드))
        self.selected_sensors = {}
        
        # 차트에 표시할 시간 범위 (기본: 1시간)
        self.current_hours = 1
        
        # 센서별 차트 선 색상 정의
        self.chart_colors = [
            '#1E88E5',  # 파랑
            '#E53935',  # 빨강
            '#43A047',  # 초록
            '#FB8C00',  # 주황
            '#8E24AA',  # 보라
            '#00ACC1',  # 청록
            '#FDD835',  # 노랑
            '#D81B60',  # 핑크
        ]
        
        # UI 생성
        self.init_ui()
        
        # 기본 센서 선택 (HP_1 온도)
        self.set_default_selection()
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 자동 새로고침 타이머 설정
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(self.ui_refresh_interval * 1000)
        
        # 시간 표시 및 카운트다운 타이머 (1초마다 실행)
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time_label)
        self.time_timer.start(1000)
        
        # 타이머 시작 확인 로그
        logger.info(f"✅ 자동 새로고침 타이머 시작")
        logger.info(f"   - 데이터 수집 주기: {self.collection_interval}초")
        logger.info(f"   - UI 갱신 주기: {self.ui_refresh_interval}초")
    
    def init_ui(self):
        """UI 초기화 및 레이아웃 구성"""
        # 윈도우 타이틀 및 크기 설정
        self.setWindowTitle('📊 여주 센서 모니터링 시스템 v1.0')
        self.setGeometry(100, 100, 1600, 900)
        
        # 스타일시트 적용
        self.setStyleSheet(Theme.get_main_stylesheet())
        
        # 중앙 위젯 생성
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃 (가로 방향)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 스플리터 (사용자가 크기 조절 가능)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 왼쪽: 센서 선택 사이드바
        sidebar = self.create_sidebar()
        splitter.addWidget(sidebar)
        
        # 오른쪽: 메인 컨텐츠 영역
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 헤더
        header_layout = self.create_header()
        right_layout.addLayout(header_layout)
        
        # 컨트롤 바
        control_bar = self.create_control_bar()
        right_layout.addWidget(control_bar)
        
        # 선택된 센서 표시 레이블
        self.selected_label = QLabel('선택된 센서: 없음')
        self.selected_label.setFont(Theme.font(10))
        self.selected_label.setStyleSheet('color: #666; padding: 5px;')
        right_layout.addWidget(self.selected_label)
        
        # 시계열 차트
        chart_group = self.create_chart()
        right_layout.addWidget(chart_group)
        
        # 통계 테이블
        stats_group = self.create_stats_table()
        right_layout.addWidget(stats_group)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # 스플리터 비율 설정 (왼쪽 300px, 오른쪽 1200px)
        splitter.setSizes([300, 1200])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 설정 메뉴
        settings_menu = menubar.addMenu('⚙️ 설정')
        
        # IP 설정
        ip_action = settings_menu.addAction('🌐 플라스틱 함 IP 설정')
        ip_action.triggered.connect(self.show_ip_config_dialog)
        
        # 전력량계 설정
        power_action = settings_menu.addAction('⚡ 전력량계 설정')
        power_action.triggered.connect(self.show_power_config_dialog)
        
        settings_menu.addSeparator()
        
        # 종료
        exit_action = settings_menu.addAction('✗ 종료')
        exit_action.triggered.connect(self.close)
    
    def show_ip_config_dialog(self):
        """IP 설정 다이얼로그 표시"""
        from ui.dialogs import IPConfigDialog
        dialog = IPConfigDialog(self)
        dialog.exec()
    
    def show_power_config_dialog(self):
        """전력량계 설정 다이얼로그 표시"""
        from ui.dialogs import PowerMeterConfigDialog
        dialog = PowerMeterConfigDialog(self)
        dialog.exec()
    
    def create_header(self):
        """헤더 영역 생성"""
        header_layout = QHBoxLayout()
        
        # 타이틀
        title = QLabel('📊 여주 센서 모니터링 시스템')
        title.setFont(Theme.font(20, bold=True))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 다음 갱신까지 시간
        self.next_refresh_label = QLabel(f'다음 갱신: {self.ui_refresh_interval}초 후')
        self.next_refresh_label.setFont(Theme.font(9))
        self.next_refresh_label.setStyleSheet('color: #999;')
        header_layout.addWidget(self.next_refresh_label)
        
        # 마지막 갱신 시간
        self.last_update_label = QLabel('마지막 갱신: --')
        self.last_update_label.setFont(Theme.font(9))
        self.last_update_label.setStyleSheet('color: #666;')
        header_layout.addWidget(self.last_update_label)
        
        # 상태
        self.status_label = QLabel('🟢 정상')
        self.status_label.setFont(Theme.font(12))
        header_layout.addWidget(self.status_label)
        
        # 현재 시간
        self.time_label = QLabel(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.time_label.setFont(Theme.font(10))
        header_layout.addWidget(self.time_label)
        
        return header_layout

    def create_sidebar(self):
        """사이드바 생성"""
        sidebar = QGroupBox('센서 선택')
        sidebar.setMaximumWidth(300)
        sidebar.setMinimumWidth(250)
        
        layout = QVBoxLayout()
        
        # 안내 문구
        info_label = QLabel('📌 센서를 체크하여 선택하세요\n(여러 개 선택 가능)')
        info_label.setFont(Theme.font(9))
        info_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(info_label)
        
        # 새로고침 버튼
        refresh_sensor_btn = QPushButton('🔄 센서 목록 새로고침')
        refresh_sensor_btn.setFont(Theme.font(9))
        refresh_sensor_btn.setToolTip('데이터베이스에서 센서 목록을 다시 불러옵니다')
        refresh_sensor_btn.clicked.connect(self.refresh_sensor_list)
        layout.addWidget(refresh_sensor_btn)
        
        # 센서 트리 위젯
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFont(Theme.font(10))
        layout.addWidget(self.tree)
        
        # 측정 항목 선택
        field_group = QGroupBox('측정 항목')
        field_layout = QVBoxLayout()
        
        self.field_group_buttons = QButtonGroup()
        self.field_radios = {}
        
        fields = [
            ('t_in', '🌡️ 입구 온도 (°C)', ['heatpump']),
            ('t_out', '🌡️ 출구 온도 (°C)', ['heatpump']),
            ('flow', '💧 유량 (L/min)', ['heatpump']),
            ('total_energy', '📈 전력량 (kWh)', ['power']),
        ]
        
        for idx, (field_key, label, sensor_types) in enumerate(fields):
            radio = QRadioButton(label)
            radio.setFont(Theme.font(9))
            radio.setProperty('sensor_types', sensor_types)
            self.field_radios[field_key] = radio
            self.field_group_buttons.addButton(radio, idx)
            field_layout.addWidget(radio)
            
            # 기본값: 입구 온도
            if field_key == 't_in':
                radio.setChecked(True)
        
        field_group.setLayout(field_layout)
        layout.addWidget(field_group)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton('✓ 적용')
        apply_btn.setFont(Theme.font(10, bold=True))
        apply_btn.clicked.connect(self.on_apply_selection)
        btn_layout.addWidget(apply_btn)
        
        clear_btn = QPushButton('✗ 초기화')
        clear_btn.setFont(Theme.font(10))
        clear_btn.clicked.connect(self.on_clear_selection)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        
        sidebar.setLayout(layout)
        
        # 센서 트리 구축
        self.build_sensor_tree()
        
        return sidebar
    
    def refresh_sensor_list(self):
        """센서 목록 새로고침"""
        try:
            logger.info('센서 목록 새로고침 시작...')
            
            # 현재 선택 상태 저장
            current_selection = {}
            for i in range(self.tree.topLevelItemCount()):
                category = self.tree.topLevelItem(i)
                for j in range(category.childCount()):
                    item = category.child(j)
                    if item.checkState(0) == Qt.CheckState.Checked:
                        data = item.data(0, Qt.ItemDataRole.UserRole)
                        if data:
                            current_selection[data['device']] = True
            
            # 센서 트리 재구성 (DB에서 최신 센서 목록 조회)
            self.build_sensor_tree()
            
            # 이전 선택 상태 복원
            restored_count = 0
            for i in range(self.tree.topLevelItemCount()):
                category = self.tree.topLevelItem(i)
                for j in range(category.childCount()):
                    item = category.child(j)
                    data = item.data(0, Qt.ItemDataRole.UserRole)
                    if data and data['device'] in current_selection:
                        item.setCheckState(0, Qt.CheckState.Checked)
                        restored_count += 1
            
            # 센서 개수 계산
            power_count = 0
            heatpump_count = 0
            
            for i in range(self.tree.topLevelItemCount()):
                category = self.tree.topLevelItem(i)
                if '전력량계' in category.text(0):
                    power_count = category.childCount()
                elif '히트펌프' in category.text(0):
                    heatpump_count = category.childCount()
            
            logger.info(f'✓ 센서 목록 새로고침 완료: 전력량계 {power_count}개, 히트펌프 {heatpump_count}개')
            logger.info(f'✓ 이전 선택 상태 {restored_count}개 복원')
            
            # 사용자 알림
            QMessageBox.information(
                self,
                '센서 목록 새로고침',
                f'센서 목록이 새로고침되었습니다.\n\n'
                f'⚡ 전력량계: {power_count}개\n'
                f'🌡️ 히트펌프: {heatpump_count}개\n\n'
                f'선택 상태 복원: {restored_count}개'
            )
            
        except Exception as e:
            logger.error(f'센서 목록 새로고침 실패: {e}', exc_info=True)
            QMessageBox.warning(
                self,
                '오류',
                f'센서 목록 새로고침 실패:\n{str(e)}'
            )
    
    def build_sensor_tree(self):
        """센서 트리 구조 생성"""
        self.tree.clear()
        
        # 전력량계 센서
        power_root = QTreeWidgetItem(self.tree, ['⚡ 전력량계'])
        power_root.setFont(0, Theme.font(10, bold=True))
        power_root.setExpanded(True)
        
        power_devices = self.service.get_all_power_devices()
        for device in power_devices:
            item = QTreeWidgetItem(power_root, [device])
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'power', 'device': device})
        
        # 히트펌프 센서
        heatpump_root = QTreeWidgetItem(self.tree, ['🌡️ 히트펌프'])
        heatpump_root.setFont(0, Theme.font(10, bold=True))
        heatpump_root.setExpanded(True)
        
        heatpump_devices = self.service.get_all_heatpump_devices()
        for device in heatpump_devices:
            item = QTreeWidgetItem(heatpump_root, [device])
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'heatpump', 'device': device})
    
    def create_control_bar(self):
        """컨트롤 바 생성"""
        control_group = QGroupBox('설정')
        control_layout = QHBoxLayout()
        
        # 시간 범위
        time_label = QLabel('⏱️ 시간 범위:')
        time_label.setFont(Theme.font(10))
        control_layout.addWidget(time_label)
        
        self.time_buttons = QButtonGroup()
        time_ranges = [
            (1, '1시간'),
            (6, '6시간'),
            (24, '24시간'),
            (168, '7일'),
        ]
        
        for idx, (hours, label) in enumerate(time_ranges):
            btn = QPushButton(label)
            btn.setFont(Theme.font(9))
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, h=hours: self.on_time_range_changed(h))
            self.time_buttons.addButton(btn, idx)
            control_layout.addWidget(btn)
            
            if hours == 1:
                btn.setChecked(True)
        
        control_layout.addStretch()
        
        # 자동 새로고침 주기 표시
        auto_refresh_label = QLabel(
            f'🔄 자동 새로고침: {self.ui_refresh_interval}초 '
            f'(수집 {self.collection_interval}초 + 여유 3초)'
        )
        auto_refresh_label.setFont(Theme.font(9))
        auto_refresh_label.setStyleSheet('color: #666;')
        control_layout.addWidget(auto_refresh_label)
        
        # 내보내기
        export_label = QLabel('📥 내보내기:')
        export_label.setFont(Theme.font(10))
        control_layout.addWidget(export_label)
        
        csv_btn = QPushButton('CSV')
        csv_btn.setFont(Theme.font(9))
        csv_btn.clicked.connect(lambda: self.export_data('csv'))
        control_layout.addWidget(csv_btn)
        
        excel_btn = QPushButton('Excel')
        excel_btn.setFont(Theme.font(9))
        excel_btn.clicked.connect(lambda: self.export_data('excel'))
        control_layout.addWidget(excel_btn)
        
        # 수동 새로고침
        refresh_btn = QPushButton('🔄 새로고침')
        refresh_btn.setFont(Theme.font(9, bold=True))
        refresh_btn.clicked.connect(self.update_data)
        control_layout.addWidget(refresh_btn)
        
        control_group.setLayout(control_layout)
        return control_group
    
    def create_chart(self):
        """시계열 차트 생성"""
        chart_group = QGroupBox(f'📈 시계열 차트 (최근 {self.current_hours}시간)')
        chart_layout = QVBoxLayout()
        
        # PyQtGraph 차트
        self.chart = pg.PlotWidget()
        self.chart.setBackground('w')
        self.chart.showGrid(x=True, y=True, alpha=0.3)
        self.chart.setLabel('left', '값')
        self.chart.setLabel('bottom', '시간')
        
        # X축 설정
        bottom_axis = self.chart.getPlotItem().getAxis('bottom')
        bottom_axis.enableAutoSIPrefix(False)
        bottom_axis.setPen(pg.mkPen(color='#333', width=1))
        
        # Y축 설정
        left_axis = self.chart.getPlotItem().getAxis('left')
        left_axis.setPen(pg.mkPen(color='#333', width=1))
        
        self.chart.addLegend()
        
        chart_layout.addWidget(self.chart)
        chart_group.setLayout(chart_layout)
        
        return chart_group
    
    def create_stats_table(self):
        """통계 테이블 생성"""
        stats_group = QGroupBox('📊 통계 (최근 24시간)')
        stats_layout = QVBoxLayout()
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(6)
        self.stats_table.setHorizontalHeaderLabels([
            '센서', '최신', '평균', '최대', '최소', '데이터 개수'
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_table.setMaximumHeight(200)
        
        stats_layout.addWidget(self.stats_table)
        stats_group.setLayout(stats_layout)
        
        return stats_group
    
    def set_default_selection(self):
        """기본값 설정: HP_1 입구 온도"""
        # HP_1 자동 체크
        for i in range(self.tree.topLevelItemCount()):
            category = self.tree.topLevelItem(i)
            if '히트펌프' in category.text(0):
                for j in range(category.childCount()):
                    item = category.child(j)
                    data = item.data(0, Qt.ItemDataRole.UserRole)
                    if data and data['device'] == 'HP_1':
                        item.setCheckState(0, Qt.CheckState.Checked)
                        break
        
        # 선택된 센서 설정
        self.selected_sensors = {
            'HP_1': ('heatpump', 't_in')
        }
        
        self.selected_label.setText('선택된 센서: HP_1 | 측정 항목: 입구 온도')
        
        # 초기 데이터 로드
        self.update_data()
    
    def update_time_label(self):
        """시간 레이블 업데이트"""
        self.time_label.setText(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.seconds_until_refresh -= 1
        if self.seconds_until_refresh < 0:
            self.seconds_until_refresh = self.ui_refresh_interval
        
        self.next_refresh_label.setText(f'다음 갱신: {self.seconds_until_refresh}초 후')

    def on_apply_selection(self):
        """적용 버튼 클릭"""
        # 선택된 측정 항목 찾기
        selected_field = None
        sensor_types = []
        
        for field_key, radio in self.field_radios.items():
            if radio.isChecked():
                selected_field = field_key
                sensor_types = radio.property('sensor_types')
                break
        
        if not selected_field:
            QMessageBox.warning(self, '경고', '측정 항목을 선택하세요.')
            return
        
        # 선택된 센서 수집
        self.selected_sensors = {}
        
        for i in range(self.tree.topLevelItemCount()):
            category = self.tree.topLevelItem(i)
            for j in range(category.childCount()):
                item = category.child(j)
                if item.checkState(0) == Qt.CheckState.Checked:
                    data = item.data(0, Qt.ItemDataRole.UserRole)
                    device = data['device']
                    sensor_type = data['type']
                    
                    # 센서 타입과 측정 항목이 호환되는지 확인
                    if sensor_type in sensor_types:
                        self.selected_sensors[device] = (sensor_type, selected_field)
        
        if not self.selected_sensors:
            QMessageBox.warning(
                self, 
                '경고', 
                '센서를 선택하거나\n해당 센서 타입에 맞는 측정 항목을 선택하세요.'
            )
            return
        
        # 선택된 센서 표시
        sensor_names = ', '.join(self.selected_sensors.keys())
        
        # 측정 항목 이름 추출
        for radio in self.field_radios.values():
            if radio.isChecked():
                field_name = radio.text().split(' ', 1)[1]
                break
        
        self.selected_label.setText(f'선택된 센서: {sensor_names} | 측정 항목: {field_name}')
        
        # 데이터 갱신
        self.update_data()
    
    def on_clear_selection(self):
        """초기화 버튼 클릭"""
        # 모든 센서 체크 해제
        for i in range(self.tree.topLevelItemCount()):
            category = self.tree.topLevelItem(i)
            for j in range(category.childCount()):
                item = category.child(j)
                item.setCheckState(0, Qt.CheckState.Unchecked)
        
        self.selected_sensors = {}
        self.selected_label.setText('선택된 센서: 없음')
        
        # 차트 및 테이블 초기화
        self.chart.clear()
        self.chart.addLegend()
        self.stats_table.setRowCount(0)
    
    def on_time_range_changed(self, hours):
        """시간 범위 변경"""
        self.current_hours = hours
        
        # 차트 그룹 타이틀 변경
        parent = self.chart.parent()
        if parent:
            parent.setTitle(f'📈 시계열 차트 (최근 {hours}시간)')
        
        # 선택된 센서가 있으면 데이터 갱신
        if self.selected_sensors:
            self.update_data()
    
    def update_data(self):
        """데이터 갱신"""
        if not self.selected_sensors:
            return
        
        self.status_label.setText('🔄 갱신 중...')
        
        try:
            # 차트 초기화
            self.chart.clear()
            self.chart.addLegend()
            
            all_timestamps = []
            
            # 각 센서별 데이터 조회 및 그래프 그리기
            for idx, (device, (sensor_type, field)) in enumerate(self.selected_sensors.items()):
                color = self.chart_colors[idx % len(self.chart_colors)]
                
                # 데이터 조회
                if sensor_type == 'heatpump':
                    timeseries = self.service.get_timeseries_heatpump(
                        device,
                        hours=self.current_hours,
                        field=field
                    )
                elif sensor_type == 'power':
                    timeseries = self.service.get_timeseries_power(
                        device,
                        hours=self.current_hours,
                        field=field
                    )
                else:
                    continue
                
                # 차트에 추가
                if timeseries:
                    timestamps = [data['timestamp'].timestamp() for data in timeseries]
                    values = [data['value'] for data in timeseries]
                    
                    if timestamps:
                        all_timestamps.extend(timestamps)
                        
                        pen = pg.mkPen(color=color, width=2)
                        self.chart.plot(
                            timestamps,
                            values,
                            pen=pen,
                            name=device
                        )
            
            # X축 시간 눈금 설정
            if all_timestamps:
                axis = self.chart.getPlotItem().getAxis('bottom')
                axis.setTicks([self.generate_time_ticks(all_timestamps)])
                
                # X축 범위 설정 (여유 공간 5%)
                min_ts = min(all_timestamps)
                max_ts = max(all_timestamps)
                time_range = max_ts - min_ts
                padding = time_range * 0.05 if time_range > 0 else 1
                self.chart.setXRange(min_ts - padding, max_ts + padding, padding=0)
            
            # 통계 테이블 업데이트
            self.update_stats_table()
            
            # 갱신 시간 기록
            self.seconds_until_refresh = self.ui_refresh_interval
            now = datetime.now()
            self.last_update_label.setText(f'마지막 갱신: {now.strftime("%H:%M:%S")}')
            self.status_label.setText('🟢 정상')
            
        except Exception as e:
            self.status_label.setText('🔴 오류')
            logger.error(f"데이터 갱신 실패: {e}", exc_info=True)
    
    def generate_time_ticks(self, timestamps):
        """X축 시간 눈금 생성"""
        if not timestamps:
            return []
        
        ticks = []
        start_ts = min(timestamps)
        end_ts = max(timestamps)
        duration = end_ts - start_ts
        
        # 시간 범위에 따라 눈금 간격 및 포맷 결정
        if duration <= 3600:  # 1시간 이하
            interval = 600  # 10분
            time_format = '%H:%M'
        elif duration <= 21600:  # 6시간 이하
            interval = 3600  # 1시간
            time_format = '%H:%M'
        elif duration <= 86400:  # 24시간 이하
            interval = 7200  # 2시간
            time_format = '%H:%M'
        else:  # 24시간 초과
            interval = 86400  # 1일
            time_format = '%m-%d'
        
        # 눈금 생성
        current_ts = start_ts
        while current_ts <= end_ts:
            dt = datetime.fromtimestamp(current_ts)
            time_str = dt.strftime(time_format)
            ticks.append((current_ts, time_str))
            current_ts += interval
        
        # 마지막 시간 추가
        if ticks and ticks[-1][0] != end_ts:
            dt = datetime.fromtimestamp(end_ts)
            time_str = dt.strftime(time_format)
            ticks.append((end_ts, time_str))
        
        return ticks
    
    def update_stats_table(self):
        """통계 테이블 업데이트"""
        self.stats_table.setRowCount(len(self.selected_sensors))
        
        for row, (device, (sensor_type, field)) in enumerate(self.selected_sensors.items()):
            # 통계 데이터 조회
            if sensor_type == 'heatpump':
                stats = self.service.get_statistics_heatpump(device, hours=24, field=field)
            elif sensor_type == 'power':
                stats = self.service.get_statistics_power(device, hours=24, field=field)
            else:
                continue
            
            # 단위 가져오기
            unit = self.get_unit(field)
            
            # 테이블 아이템 생성
            items = [
                device,
                f"{stats['latest']} {unit}",
                f"{stats['avg']} {unit}",
                f"{stats['max']} {unit}",
                f"{stats['min']} {unit}",
                f"{stats['count']}개"
            ]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.stats_table.setItem(row, col, item)
    
    def export_data(self, format_type):
        """데이터 내보내기"""
        if not self.selected_sensors:
            QMessageBox.warning(self, '경고', '내보낼 센서를 선택하세요.')
            return
        
        # 파일 저장 대화상자
        if format_type == 'csv':
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                'CSV 저장',
                f'sensor_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'CSV Files (*.csv)'
            )
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                'Excel 저장',
                f'sensor_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                'Excel Files (*.xlsx)'
            )
        
        if not file_path:
            return
        
        try:
            all_data = []
            
            # 각 센서별 데이터 수집
            for device, (sensor_type, field) in self.selected_sensors.items():
                if sensor_type == 'heatpump':
                    timeseries = self.service.get_timeseries_heatpump(
                        device,
                        hours=self.current_hours,
                        field=field
                    )
                elif sensor_type == 'power':
                    timeseries = self.service.get_timeseries_power(
                        device,
                        hours=self.current_hours,
                        field=field
                    )
                else:
                    continue
                
                for record in timeseries:
                    all_data.append({
                        '센서': device,
                        '시간': record['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        '측정 항목': field,
                        '값': record['value'],
                        '단위': self.get_unit(field)
                    })
            
            # DataFrame 생성
            df = pd.DataFrame(all_data)
            
            # 파일 저장
            if format_type == 'csv':
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(file_path, index=False)
            
            QMessageBox.information(
                self,
                '완료',
                f'데이터가 저장되었습니다.\n\n파일: {file_path}\n레코드 수: {len(all_data)}개'
            )
            
        except Exception as e:
            QMessageBox.critical(self, '오류', f'데이터 저장 실패:\n{str(e)}')
    
    def get_unit(self, field):
        """측정 항목 단위 반환"""
        units = {
            't_in': '°C',
            't_out': '°C',
            'flow': 'L/min',
            'energy': 'kWh',
            'v': 'V',
            'a': 'A',
            'w': 'W',
            'wh': 'Wh',
        }
        return units.get(field, '')
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        self.timer.stop()
        self.time_timer.stop()
        logger.info("GUI 종료")
        event.accept()
