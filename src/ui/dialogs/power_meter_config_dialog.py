# ==============================================
# 전력량계 설정 다이얼로그
# ==============================================
"""
전력량계 설정 다이얼로그

기능:
- Slave ID 설정
- 활성화/비활성화
- JSON 파일 저장
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt

from ui.theme import Theme


class PowerMeterConfigDialog(QDialog):
    """전력량계 설정 다이얼로그"""
    
    def __init__(self, parent=None):
        """초기화"""
        super().__init__(parent)
        self.setWindowTitle('전력량계 설정')
        self.setMinimumSize(800, 600)
        
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
        layout.addWidget(title)
        
        # 설명
        desc = QLabel('전력량계의 Slave ID를 설정합니다.')
        desc.setFont(Theme.font(10))
        desc.setStyleSheet('color: #666;')
        layout.addWidget(desc)
        
        # IP 표시
        self.ip_label = QLabel('IP: --')
        self.ip_label.setFont(Theme.font(11, bold=True))
        layout.addWidget(self.ip_label)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            'ID', '이름', 'Slave ID', '활성화', '설명'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton('💾 저장')
        save_btn.setFont(Theme.font(11, bold=True))
        save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton('✗ 취소')
        cancel_btn.setFont(Theme.font(11))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_config(self):
        """설정 파일 로드"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # IP 표시
            ip = self.config_data.get('ip', '--')
            port = self.config_data.get('port', '--')
            self.ip_label.setText(f'IP: {ip}:{port}')
            
            # 전력량계 목록
            meters = self.config_data.get('meters', [])
            self.table.setRowCount(len(meters))
            
            for row, meter in enumerate(meters):
                self.table.setItem(row, 0, QTableWidgetItem(meter['device_id']))
                self.table.setItem(row, 1, QTableWidgetItem(meter['name']))
                self.table.setItem(row, 2, QTableWidgetItem(str(meter['slave_id'])))
                self.table.setItem(row, 3, QTableWidgetItem('활성' if meter['enabled'] else '비활성'))
                self.table.setItem(row, 4, QTableWidgetItem(meter.get('description', '')))
        
        except Exception as e:
            QMessageBox.critical(self, '오류', f'설정 파일 로드 실패:\n{str(e)}')
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            # 테이블 데이터를 config_data에 반영
            meters = []
            
            for row in range(self.table.rowCount()):
                device_id = self.table.item(row, 0).text()
                name = self.table.item(row, 1).text()
                slave_id = int(self.table.item(row, 2).text())
                enabled = self.table.item(row, 3).text() == '활성'
                description = self.table.item(row, 4).text()
                
                meter = {
                    'id': row + 1,
                    'device_id': device_id,
                    'name': name,
                    'slave_id': slave_id,
                    'description': description,
                    'enabled': enabled
                }
                
                meters.append(meter)
            
            self.config_data['meters'] = meters
            
            # 파일 저장
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, '저장 완료', '설정이 저장되었습니다.')
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, '오류', f'설정 저장 실패:\n{str(e)}')
