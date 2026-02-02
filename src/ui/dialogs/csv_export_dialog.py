# ==============================================
# CSV 내보내기 다이얼로그
# ==============================================
"""
데이터 CSV 내보내기 다이얼로그

기능:
- 센서 타입 선택 (히트펌프/지중배관/전력량계)
- 날짜 범위 지정
- 장치 선택
- 파일 형식 선택 (단일 파일/장치별 파일)
- 출력 디렉토리 선택
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QRadioButton, QCheckBox,
    QDateTimeEdit, QFileDialog, QLineEdit, QMessageBox,
    QProgressDialog, QListWidget, QButtonGroup
)
from PyQt6.QtCore import Qt, QDateTime, QThread, pyqtSignal

from ui.theme import Theme
from services.csv_export_service import CSVExportService
from services.ui_data_service import UIDataService

logger = logging.getLogger(__name__)


class ExportWorker(QThread):
    """CSV 내보내기 작업 스레드"""
    
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    
    def __init__(self, service, sensor_type, output_dir, start_date, end_date, single_file, device_ids):
        super().__init__()
        self.service = service
        self.sensor_type = sensor_type
        self.output_dir = output_dir
        self.start_date = start_date
        self.end_date = end_date
        self.single_file = single_file
        self.device_ids = device_ids
    
    def run(self):
        """작업 실행"""
        try:
            self.progress.emit(f"{self.sensor_type} 데이터 내보내기 중...")
            
            if self.sensor_type == '히트펌프':
                result = self.service.export_heatpump_data(
                    output_dir=self.output_dir,
                    device_ids=self.device_ids,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    single_file=self.single_file
                )
            elif self.sensor_type == '지중배관':
                result = self.service.export_groundpipe_data(
                    output_dir=self.output_dir,
                    device_ids=self.device_ids,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    single_file=self.single_file
                )
            elif self.sensor_type == '전력량계':
                result = self.service.export_power_meter_data(
                    output_dir=self.output_dir,
                    device_ids=self.device_ids,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    single_file=self.single_file
                )
            else:
                result = {'success': False, 'files': [], 'total_rows': 0}
            
            self.finished.emit(result)
        
        except Exception as e:
            logger.error(f"CSV 내보내기 오류: {e}", exc_info=True)
            self.finished.emit({'success': False, 'files': [], 'total_rows': 0, 'error': str(e)})


class CSVExportDialog(QDialog):
    """CSV 내보내기 다이얼로그"""
    
    def __init__(self, parent=None):
        """초기화"""
        super().__init__(parent)
        
        self.setWindowTitle('CSV 파일 내보내기')
        self.setMinimumSize(800, 700)
        
        self.csv_service = CSVExportService()
        self.data_service = UIDataService()
        
        self.init_ui()
        self.load_devices()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 제목
        title = QLabel('📊 CSV 파일 내보내기')
        title.setFont(Theme.font(16, bold=True))
        title.setStyleSheet(f'color: {Theme.PRIMARY}; padding: 10px;')
        layout.addWidget(title)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 센서 타입 선택
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        sensor_group = QGroupBox('1. 센서 타입 선택')
        sensor_group.setFont(Theme.font(12, bold=True))
        sensor_layout = QHBoxLayout()
        
        self.sensor_type_group = QButtonGroup()
        
        self.rb_heatpump = QRadioButton('🌡️ 히트펌프')
        self.rb_heatpump.setFont(Theme.font(11))
        self.rb_heatpump.setChecked(True)
        self.rb_heatpump.toggled.connect(self.on_sensor_type_changed)
        self.sensor_type_group.addButton(self.rb_heatpump, 0)
        sensor_layout.addWidget(self.rb_heatpump)
        
        self.rb_groundpipe = QRadioButton('🌊 지중배관')
        self.rb_groundpipe.setFont(Theme.font(11))
        self.rb_groundpipe.toggled.connect(self.on_sensor_type_changed)
        self.sensor_type_group.addButton(self.rb_groundpipe, 1)
        sensor_layout.addWidget(self.rb_groundpipe)
        
        self.rb_power = QRadioButton('⚡ 전력량계')
        self.rb_power.setFont(Theme.font(11))
        self.rb_power.toggled.connect(self.on_sensor_type_changed)
        self.sensor_type_group.addButton(self.rb_power, 2)
        sensor_layout.addWidget(self.rb_power)
        
        sensor_layout.addStretch()
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 날짜 범위 선택
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        date_group = QGroupBox('2. 날짜 범위 선택')
        date_group.setFont(Theme.font(12, bold=True))
        date_layout = QVBoxLayout()
        
        # 전체 기간
        self.cb_all_dates = QCheckBox('전체 기간')
        self.cb_all_dates.setFont(Theme.font(11))
        self.cb_all_dates.setChecked(True)
        self.cb_all_dates.stateChanged.connect(self.on_all_dates_changed)
        date_layout.addWidget(self.cb_all_dates)
        
        # 날짜 범위
        date_range_layout = QHBoxLayout()
        
        start_label = QLabel('시작:')
        start_label.setFont(Theme.font(11))
        date_range_layout.addWidget(start_label)
        
        self.dt_start = QDateTimeEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.dt_start.setEnabled(False)
        self.dt_start.setFont(Theme.font(11))
        date_range_layout.addWidget(self.dt_start)
        
        date_range_layout.addSpacing(20)
        
        end_label = QLabel('종료:')
        end_label.setFont(Theme.font(11))
        date_range_layout.addWidget(end_label)
        
        self.dt_end = QDateTimeEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDateTime(QDateTime.currentDateTime())
        self.dt_end.setEnabled(False)
        self.dt_end.setFont(Theme.font(11))
        date_range_layout.addWidget(self.dt_end)
        
        date_range_layout.addStretch()
        date_layout.addLayout(date_range_layout)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 장치 선택
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        device_group = QGroupBox('3. 장치 선택')
        device_group.setFont(Theme.font(12, bold=True))
        device_layout = QVBoxLayout()
        
        # 전체 선택
        device_select_layout = QHBoxLayout()
        
        self.cb_all_devices = QCheckBox('전체 선택')
        self.cb_all_devices.setFont(Theme.font(11))
        self.cb_all_devices.setChecked(True)
        self.cb_all_devices.stateChanged.connect(self.on_all_devices_changed)
        device_select_layout.addWidget(self.cb_all_devices)
        
        device_select_layout.addStretch()
        device_layout.addLayout(device_select_layout)
        
        # 장치 목록
        self.device_list = QListWidget()
        self.device_list.setFont(Theme.font(11))
        self.device_list.setMaximumHeight(150)
        self.device_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.device_list.itemSelectionChanged.connect(self.on_device_selection_changed)
        device_layout.addWidget(self.device_list)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 파일 형식 선택
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        format_group = QGroupBox('4. 파일 형식')
        format_group.setFont(Theme.font(12, bold=True))
        format_layout = QVBoxLayout()
        
        self.format_group = QButtonGroup()
        
        self.rb_single = QRadioButton('하나의 파일로 내보내기 (모든 장치 데이터 포함)')
        self.rb_single.setFont(Theme.font(11))
        self.format_group.addButton(self.rb_single, 0)
        format_layout.addWidget(self.rb_single)
        
        self.rb_multiple = QRadioButton('장치별 파일로 내보내기 (장치마다 별도 파일)')
        self.rb_multiple.setFont(Theme.font(11))
        self.rb_multiple.setChecked(True)
        self.format_group.addButton(self.rb_multiple, 1)
        format_layout.addWidget(self.rb_multiple)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 출력 디렉토리
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        output_group = QGroupBox('5. 출력 디렉토리')
        output_group.setFont(Theme.font(12, bold=True))
        output_layout = QHBoxLayout()
        
        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setFont(Theme.font(11))
        self.txt_output_dir.setText(str(Path.home() / 'Desktop' / 'sensor_exports'))
        self.txt_output_dir.setReadOnly(True)
        output_layout.addWidget(self.txt_output_dir)
        
        btn_browse = QPushButton('📁 찾아보기')
        btn_browse.setFont(Theme.font(11))
        btn_browse.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(btn_browse)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 버튼
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        
        # 내보내기 버튼
        btn_export = QPushButton('📥 내보내기')
        btn_export.setFont(Theme.font(12, bold=True))
        btn_export.setMinimumHeight(45)
        btn_export.clicked.connect(self.start_export)
        btn_layout.addWidget(btn_export)
        
        # 취소 버튼
        btn_cancel = QPushButton('✗ 취소')
        btn_cancel.setFont(Theme.font(12))
        btn_cancel.setMinimumHeight(45)
        btn_cancel.setStyleSheet(f'background-color: {Theme.TEXT_SECONDARY};')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_devices(self):
        """장치 목록 로드"""
        self.device_list.clear()
        
        if self.rb_heatpump.isChecked():
            devices = self.data_service.get_all_heatpump_devices()
        elif self.rb_groundpipe.isChecked():
            devices = self.data_service.get_all_groundpipe_devices()
        else:
            devices = self.data_service.get_all_power_devices()
        
        for device_id in devices:
            self.device_list.addItem(device_id)
        
        # 전체 선택
        if self.cb_all_devices.isChecked():
            self.device_list.selectAll()
    
    def on_sensor_type_changed(self):
        """센서 타입 변경"""
        self.load_devices()
    
    def on_all_dates_changed(self, state):
        """전체 기간 체크박스 변경"""
        enabled = not self.cb_all_dates.isChecked()
        self.dt_start.setEnabled(enabled)
        self.dt_end.setEnabled(enabled)
    
    def on_all_devices_changed(self, state):
        """전체 장치 체크박스 변경"""
        if self.cb_all_devices.isChecked():
            self.device_list.selectAll()
        else:
            self.device_list.clearSelection()
    
    def on_device_selection_changed(self):
        """장치 선택 변경"""
        selected_count = len(self.device_list.selectedItems())
        total_count = self.device_list.count()
        
        # 전체 선택 체크박스 상태 업데이트
        if selected_count == total_count:
            self.cb_all_devices.setChecked(True)
        else:
            self.cb_all_devices.setChecked(False)
    
    def browse_output_dir(self):
        """출력 디렉토리 선택"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            '출력 디렉토리 선택',
            str(Path.home() / 'Desktop')
        )
        
        if dir_path:
            self.txt_output_dir.setText(dir_path)
    
    def start_export(self):
        """내보내기 시작"""
        # 장치 선택 확인
        selected_items = self.device_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '경고', '장치를 선택해주세요.')
            return
        
        device_ids = [item.text() for item in selected_items]
        
        # 날짜 범위
        start_date = None if self.cb_all_dates.isChecked() else self.dt_start.dateTime().toPyDateTime()
        end_date = None if self.cb_all_dates.isChecked() else self.dt_end.dateTime().toPyDateTime()
        
        # 파일 형식
        single_file = self.rb_single.isChecked()
        
        # 출력 디렉토리
        output_dir = self.txt_output_dir.text()
        
        # 센서 타입
        if self.rb_heatpump.isChecked():
            sensor_type = '히트펌프'
        elif self.rb_groundpipe.isChecked():
            sensor_type = '지중배관'
        else:
            sensor_type = '전력량계'
        
        # 프로그레스 다이얼로그
        self.progress_dialog = QProgressDialog('내보내기 중...', '취소', 0, 0, self)
        self.progress_dialog.setWindowTitle('CSV 내보내기')
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()
        
        # 작업 스레드 시작
        self.worker = ExportWorker(
            self.csv_service,
            sensor_type,
            output_dir,
            start_date,
            end_date,
            single_file,
            device_ids
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.start()
    
    def on_progress(self, message):
        """진행 상황 업데이트"""
        self.progress_dialog.setLabelText(message)
    
    def on_export_finished(self, result):
        """내보내기 완료"""
        self.progress_dialog.close()
        
        if result['success']:
            file_list = '\n'.join([f"  - {Path(f).name}" for f in result['files'][:10]])
            if len(result['files']) > 10:
                file_list += f"\n  ... 외 {len(result['files']) - 10}개"
            
            QMessageBox.information(
                self,
                '내보내기 완료',
                f"✓ CSV 파일 내보내기 완료\n\n"
                f"파일 개수: {len(result['files'])}개\n"
                f"총 데이터: {result['total_rows']:,}행\n\n"
                f"저장된 파일:\n{file_list}\n\n"
                f"위치: {self.txt_output_dir.text()}"
            )
            self.accept()
        else:
            error_msg = result.get('error', '알 수 없는 오류')
            QMessageBox.critical(
                self,
                '내보내기 실패',
                f"✗ CSV 파일 내보내기 실패\n\n오류: {error_msg}"
            )


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from core.logging_config import setup_logging
    from core.database import initialize_connection_pool
    
    setup_logging(log_level="DEBUG")
    initialize_connection_pool()
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    dialog = CSVExportDialog()
    dialog.exec()
    
    sys.exit(app.exec())
