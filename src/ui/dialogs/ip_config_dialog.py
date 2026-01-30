# ==============================================
# IP 설정 다이얼로그
# ==============================================
"""
플라스틱 함 (히트펌프/지중배관) IP 설정 다이얼로그

기능:
- 장치 IP 주소 설정
- 포트 설정
- 활성화/비활성화
- Description 편집
- JSON 파일 저장
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QCheckBox,
)
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt

from ui.theme import Theme


class IPConfigDialog(QDialog):
    """IP 설정 다이얼로그"""
    
    def __init__(self, parent=None):
        """초기화"""
        super().__init__(parent)
        self.setWindowTitle('장치별 IP 설정')
        self.setMinimumSize(1000, 700)
        
        self.config_file = Path('config/box_ips.json')
        self.config_data = None
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제목
        title = QLabel('🌡️ 장치별 센서 IP 설정')
        title.setFont(Theme.font(16, bold=True))
        title.setStyleSheet(f'color: {Theme.PRIMARY}; padding: 10px;')
        layout.addWidget(title)
        
        # 설명
        desc = QLabel(
            '히트펌프와 지중배관의 IP 주소, 포트, 설명을 설정합니다.\n'
            '셀을 더블클릭하여 수정할 수 있습니다.'
        )
        desc.setFont(Theme.font(10))
        desc.setStyleSheet(f'color: {Theme.TEXT_SECONDARY}; padding: 5px;')
        layout.addWidget(desc)
        
        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            'ID', '이름', 'IP 주소', '포트', '활성화', '설명', '타입'
        ])
        
        # 컬럼 너비 설정
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 이름
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # IP
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 포트
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 활성화
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # 설명
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 타입
        
        self.table.setColumnWidth(2, 150)  # IP 주소 컬럼 너비
        
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
            
            # 히트펌프
            heatpumps = self.config_data.get('heatpump', [])
            
            # 지중배관
            pipes = self.config_data.get('groundpipe', [])
            
            # 테이블에 표시
            all_devices = []
            for hp in heatpumps:
                hp['type'] = 'heatpump'
                all_devices.append(hp)
            for pipe in pipes:
                pipe['type'] = 'groundpipe'
                all_devices.append(pipe)
            
            self.table.setRowCount(len(all_devices))
            
            for row, device in enumerate(all_devices):
                # ID
                id_item = QTableWidgetItem(device['device_id'])
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, id_item)
                
                # 이름
                name_item = QTableWidgetItem(device['name'])
                self.table.setItem(row, 1, name_item)
                
                # IP 주소
                ip_item = QTableWidgetItem(device['ip'])
                self.table.setItem(row, 2, ip_item)
                
                # 포트
                port_item = QTableWidgetItem(str(device['port']))
                port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, port_item)
                
                # 활성화 (체크박스)
                enabled_widget = QCheckBox()
                enabled_widget.setChecked(device['enabled'])
                enabled_widget.setStyleSheet('margin-left: 35px;')
                self.table.setCellWidget(row, 4, enabled_widget)
                
                # 설명
                desc_item = QTableWidgetItem(device.get('description', ''))
                self.table.setItem(row, 5, desc_item)
                
                # 타입 (수정된 부분)
                type_item = QTableWidgetItem('히트펌프' if device['type'] == 'heatpump' else '지중배관')
                type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # ✅ QBrush 사용
                color = Theme.HEATPUMP_COLOR if device['type'] == 'heatpump' else Theme.PIPE_COLOR
                type_item.setForeground(QBrush(QColor(color)))

                self.table.setItem(row, 6, type_item)
        
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
                enabled = self.table.cellWidget(row, 4).isChecked()
                description = self.table.item(row, 5).text()
                device_type = self.table.item(row, 6).text()
                
                # 원본 데이터에서 sensors 정보 가져오기
                original_device = None
                if device_type == '히트펌프':
                    for hp in self.config_data.get('heatpump', []):
                        if hp['device_id'] == device_id:
                            original_device = hp
                            break
                else:
                    for pipe in self.config_data.get('groundpipe', []):
                        if pipe['device_id'] == device_id:
                            original_device = pipe
                            break
                
                device = {
                    'id': row + 1,
                    'device_id': device_id,
                    'name': name,
                    'ip': ip,
                    'port': port,
                    'description': description,
                    'enabled': enabled,
                    'sensors': original_device.get('sensors', {
                        'temp1_slave_id': 1,
                        'temp2_slave_id': 2,
                        'flow_slave_id': 3
                    }) if original_device else {
                        'temp1_slave_id': 1,
                        'temp2_slave_id': 2,
                        'flow_slave_id': 3
                    }
                }
                
                if device_type == '히트펌프':
                    heatpumps.append(device)
                else:
                    pipes.append(device)
            
            self.config_data['heatpump'] = heatpumps
            self.config_data['groundpipe'] = pipes
            
            # 파일 저장
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, '저장 완료', '설정이 저장되었습니다.\n변경사항을 적용하려면 프로그램을 재시작하세요.')
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
    
    dialog = IPConfigDialog()
    dialog.exec()
    
    sys.exit(app.exec())
