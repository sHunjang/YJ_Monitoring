# ==============================================
# 전력량계 설정 다이얼로그
# ==============================================
"""
전력량계 Slave ID 및 설정 다이얼로그

기능:
- Slave ID 설정
- IP/Port 설정
- 활성화/비활성화
- Description 편집
- JSON 파일 저장
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt

from ui.theme import Theme


class PowerMeterConfigDialog(QDialog):
    """전력량계 설정 다이얼로그"""
    
    def __init__(self, parent=None):
        """초기화"""
        super().__init__(parent)
        self.setWindowTitle('전력량계 설정')
        self.setMinimumSize(1200, 700)
        
        self.config_file = Path('config/power_meter_config.json')
        self.config_data = None
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제목
        title = QLabel('⚡ 전력량계 설정')
        title.setFont(Theme.font(16, bold=True))
        title.setStyleSheet(f'color: {Theme.PRIMARY}; padding: 10px;')
        layout.addWidget(title)
        
        # 설명
        desc = QLabel(
            '전력량계의 Slave ID, IP 주소, 포트, 설명을 설정합니다.\n'
            '셀을 더블클릭하여 수정할 수 있습니다.'
        )
        desc.setFont(Theme.font(10))
        desc.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; padding: 5px;')
        layout.addWidget(desc)
        
        # IP/Port 정보
        info_layout = QHBoxLayout()
        info_label = QLabel('📡 통신 설정')
        info_label.setFont(Theme.font(11, bold=True))
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # IP/Port 테이블
        self.info_table = QTableWidget()
        self.info_table.setRowCount(1)
        self.info_table.setColumnCount(2)
        self.info_table.setHorizontalHeaderLabels(['IP 주소', '포트'])
        self.info_table.verticalHeader().setVisible(False)
        self.info_table.setMaximumHeight(80)
        
        header = self.info_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.info_table)
        
        # 전력량계 목록
        meter_label = QLabel('📊 전력량계 목록')
        meter_label.setFont(Theme.font(11, bold=True))
        meter_label.setStyleSheet('margin-top: 20px;')
        layout.addWidget(meter_label)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Slave ID', '이름', '활성화', '설명'
        ])
        
        # 컬럼 너비 설정
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Slave ID
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 이름
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 활성화
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # 설명
        
        self.table.setColumnWidth(0, 80)  # ID
        self.table.setColumnWidth(1, 100)  # Slave ID
        
        layout.addWidget(self.table)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        # 새로고침 버튼
        refresh_btn = QPushButton('🔄 새로고침')
        refresh_btn.setFont(Theme.font(11))
        refresh_btn.setStyleSheet(f'background-color: {Theme.SECONDARY};')
        refresh_btn.clicked.connect(self.load_config)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        # 저장 버튼
        save_btn = QPushButton('💾 저장')
        save_btn.setFont(Theme.font(11, bold=True))
        save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(save_btn)
        
        # 취소 버튼
        cancel_btn = QPushButton('✗ 취소')
        cancel_btn.setFont(Theme.font(11))
        cancel_btn.setStyleSheet(f'background-color: {Theme.TEXT_SECONDARY};')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_config(self):
        """설정 파일 로드"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # IP/Port 정보
            ip_item = QTableWidgetItem(self.config_data['ip'])
            self.info_table.setItem(0, 0, ip_item)
            
            port_item = QTableWidgetItem(str(self.config_data['port']))
            port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.info_table.setItem(0, 1, port_item)
            
            # 전력량계 목록
            meters = self.config_data.get('meters', [])
            self.table.setRowCount(len(meters))
            
            for row, meter in enumerate(meters):
                # ID
                id_item = QTableWidgetItem(meter['device_id'])
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, id_item)
                
                # Slave ID (SpinBox)
                slave_id_spin = QSpinBox()
                slave_id_spin.setMinimum(1)
                slave_id_spin.setMaximum(247)
                slave_id_spin.setValue(meter['slave_id'])
                slave_id_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
                slave_id_spin.setStyleSheet(f"""
                    QSpinBox {{
                        background-color: {Theme.BG_SECONDARY};
                        border: 1px solid {Theme.BORDER};
                        border-radius: 5px;
                        padding: 5px;
                        font-size: 12px;
                    }}
                    QSpinBox:focus {{
                        border: 1px solid {Theme.PRIMARY};
                    }}
                """)
                self.table.setCellWidget(row, 1, slave_id_spin)
                
                # 이름
                name_item = QTableWidgetItem(meter['name'])
                self.table.setItem(row, 2, name_item)
                
                # 활성화 (체크박스)
                enabled_widget = QCheckBox()
                enabled_widget.setChecked(meter['enabled'])
                enabled_widget.setStyleSheet('margin-left: 35px;')
                self.table.setCellWidget(row, 3, enabled_widget)
                
                # 설명
                desc_item = QTableWidgetItem(meter.get('description', ''))
                self.table.setItem(row, 4, desc_item)
        
        except Exception as e:
            QMessageBox.critical(self, '오류', f'설정 파일 로드 실패:\n{str(e)}')
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            # IP/Port 정보 업데이트
            self.config_data['ip'] = self.info_table.item(0, 0).text()
            self.config_data['port'] = int(self.info_table.item(0, 1).text())
            
            # 전력량계 목록 업데이트
            meters = []
            for row in range(self.table.rowCount()):
                device_id = self.table.item(row, 0).text()
                slave_id = self.table.cellWidget(row, 1).value()
                name = self.table.item(row, 2).text()
                enabled = self.table.cellWidget(row, 3).isChecked()
                description = self.table.item(row, 4).text()
                
                meter = {
                    'id': row + 1,
                    'device_id': device_id,
                    'slave_id': slave_id,
                    'name': name,
                    'description': description,
                    'enabled': enabled
                }
                
                meters.append(meter)
            
            self.config_data['meters'] = meters
            
            # 파일 저장
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(
                self, 
                '저장 완료', 
                '설정이 저장되었습니다.\n변경사항을 적용하려면 프로그램을 재시작하세요.'
            )
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, '오류', f'설정 저장 실패:\n{str(e)}')


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 스타일시트 적용
    app.setStyleSheet(Theme.get_main_stylesheet())
    
    dialog = PowerMeterConfigDialog()
    dialog.exec()
    
    sys.exit(app.exec())
