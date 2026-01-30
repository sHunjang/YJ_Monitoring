# ==============================================
# IP 설정 다이얼로그
# ==============================================
"""
플라스틱 함 (히트펌프/지중배관) IP 설정 다이얼로그

기능:
- 장치 IP 주소 설정
- 포트 설정
- 활성화/비활성화
- JSON 파일 저장
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt

from ui.theme import Theme


class IPConfigDialog(QDialog):
    """IP 설정 다이얼로그"""
    
    def __init__(self, parent=None):
        """초기화"""
        super().__init__(parent)
        self.setWindowTitle('플라스틱 함 IP 설정')
        self.setMinimumSize(800, 600)
        
        self.config_file = Path('config/box_ips.json')
        self.config_data = None
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제목
        title = QLabel('🌡️ 플라스틱 함 센서 IP 설정')
        title.setFont(Theme.font(16, bold=True))
        layout.addWidget(title)
        
        # 설명
        desc = QLabel('히트펌프와 지중배관의 IP 주소를 설정합니다.')
        desc.setFont(Theme.font(10))
        desc.setStyleSheet('color: #666;')
        layout.addWidget(desc)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'ID', '이름', 'IP 주소', '포트', '활성화', '설명'
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
            
            # 히트펌프
            heatpumps = self.config_data.get('heatpump', [])
            
            # 지중배관
            pipes = self.config_data.get('underground_pipe', [])
            
            # 테이블에 표시
            all_devices = heatpumps + pipes
            self.table.setRowCount(len(all_devices))
            
            for row, device in enumerate(all_devices):
                self.table.setItem(row, 0, QTableWidgetItem(device['device_id']))
                self.table.setItem(row, 1, QTableWidgetItem(device['name']))
                self.table.setItem(row, 2, QTableWidgetItem(device['ip']))
                self.table.setItem(row, 3, QTableWidgetItem(str(device['port'])))
                self.table.setItem(row, 4, QTableWidgetItem('활성' if device['enabled'] else '비활성'))
                self.table.setItem(row, 5, QTableWidgetItem(device.get('description', '')))
        
        except Exception as e:
            QMessageBox.critical(self, '오류', f'설정 파일 로드 실패:\n{str(e)}')
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            # 테이블 데이터를 config_data에 반영
            heatpumps = []
            pipes = []
            
            for row in range(self.table.rowCount()):
                device_id = self.table.item(row, 0).text()
                name = self.table.item(row, 1).text()
                ip = self.table.item(row, 2).text()
                port = int(self.table.item(row, 3).text())
                enabled = self.table.item(row, 4).text() == '활성'
                description = self.table.item(row, 5).text()
                
                device = {
                    'id': row + 1,
                    'device_id': device_id,
                    'name': name,
                    'ip': ip,
                    'port': port,
                    'description': description,
                    'enabled': enabled,
                    'sensors': {
                        'temp1_slave_id': 1,
                        'temp2_slave_id': 2,
                        'flow_slave_id': 3
                    }
                }
                
                if device_id.startswith('HP_'):
                    heatpumps.append(device)
                elif device_id.startswith('UP_'):
                    pipes.append(device)
            
            self.config_data['heatpump'] = heatpumps
            self.config_data['underground_pipe'] = pipes
            
            # 파일 저장
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, '저장 완료', '설정이 저장되었습니다.')
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, '오류', f'설정 저장 실패:\n{str(e)}')
