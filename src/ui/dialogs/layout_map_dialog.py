# ==============================================
# 센서 배치도 다이얼로그
# ==============================================

import json
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QMessageBox, QLineEdit, QSpinBox, QFormLayout, QDialogButtonBox,
    QComboBox, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QPainterPath, QCursor
)

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 색상 상수 (theme.py 미사용 - 하드코딩)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C_PRIMARY      = '#1976d2'   # 파란색
C_SUCCESS      = '#388e3c'   # 초록색
C_WARNING      = '#f57c00'   # 주황색
C_DANGER       = '#c0392b'   # 빨간색
C_BG           = '#f5f5f5'   # 메인 배경
C_BG2          = '#ffffff'   # 카드 배경
C_TEXT         = '#212121'   # 메인 텍스트
C_TEXT2        = '#757575'   # 보조 텍스트
C_BORDER       = '#e0e0e0'   # 테두리
C_HP           = '#388e3c'   # 히트펌프 (초록)
C_GP           = '#f57c00'   # 지중배관 (주황)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 이미지 기준 실제 운영 데이터 + 배치 좌표
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEFAULT_DEVICES = {
    "heatpump": [
        {
            "id": 1, "device_id": "HP_1", "name": "히트펌프_1",
            "ip": "172.30.1.95", "port": 8899, "description": "히트펌프 1호기",
            "enabled": True,
            "sensors": {"temp1_slave_id": 1, "temp2_slave_id": 2, "flow_slave_id": 3},
            "pos_x": 0.07, "pos_y": 0.88
        },
        {
            "id": 2, "device_id": "HP_2", "name": "히트펌프_2",
            "ip": "172.30.1.96", "port": 8899, "description": "히트펌프 2호기",
            "enabled": True,
            "sensors": {"temp1_slave_id": 23, "temp2_slave_id": 24, "flow_slave_id": 12},
            "pos_x": 0.93, "pos_y": 0.28
        },
        {
            "id": 3, "device_id": "HP_3", "name": "히트펌프_3",
            "ip": "172.30.1.104", "port": 8899, "description": "히트펌프 3호기",
            "enabled": True,
            "sensors": {"temp1_slave_id": 25, "temp2_slave_id": 26, "flow_slave_id": 13},
            "pos_x": 0.07, "pos_y": 0.28
        },
        {
            "id": 4, "device_id": "HP_4", "name": "히트펌프_4",
            "ip": "172.30.1.105", "port": 8899, "description": "히트펌프 4호기",
            "enabled": True,
            "sensors": {"temp1_slave_id": 27, "temp2_slave_id": 28, "flow_slave_id": 14},
            "pos_x": 0.07, "pos_y": 0.63
        },
    ],
    "groundpipe": [
        {
            "id": 5, "device_id": "GP_5", "name": "지중배관_5",
            "ip": "172.30.1.97", "port": 8899, "description": "지중배관 5호",
            "enabled": True,
            "sensors": {"temp1_slave_id": 11, "temp2_slave_id": 12, "flow_slave_id": 6},
            "pos_x": 0.42, "pos_y": 0.09
        },
        {
            "id": 6, "device_id": "GP_6", "name": "지중배관_6",
            "ip": "172.30.1.98", "port": 8899, "description": "지중배관 6호",
            "enabled": True,
            "sensors": {"temp1_slave_id": 13, "temp2_slave_id": 14, "flow_slave_id": 7},
            "pos_x": 0.58, "pos_y": 0.09
        },
        {
            "id": 7, "device_id": "GP_7", "name": "지중배관_7",
            "ip": "172.30.1.99", "port": 8899, "description": "지중배관 7호",
            "enabled": True,
            "sensors": {"temp1_slave_id": 15, "temp2_slave_id": 16, "flow_slave_id": 8},
            "pos_x": 0.42, "pos_y": 0.28
        },
        {
            "id": 8, "device_id": "GP_8", "name": "지중배관_8",
            "ip": "172.30.1.101", "port": 8899, "description": "지중배관 8호",
            "enabled": True,
            "sensors": {"temp1_slave_id": 17, "temp2_slave_id": 18, "flow_slave_id": 9},
            "pos_x": 0.58, "pos_y": 0.28
        },
        {
            "id": 9, "device_id": "GP_9", "name": "지중배관_9",
            "ip": "172.30.1.102", "port": 8899, "description": "지중배관 9호",
            "enabled": True,
            "sensors": {"temp1_slave_id": 19, "temp2_slave_id": 20, "flow_slave_id": 10},
            "pos_x": 0.42, "pos_y": 0.77
        },
        {
            "id": 10, "device_id": "GP_10", "name": "지중배관_10",
            "ip": "172.30.1.103", "port": 8899, "description": "지중배관 10호",
            "enabled": True,
            "sensors": {"temp1_slave_id": 21, "temp2_slave_id": 22, "flow_slave_id": 11},
            "pos_x": 0.58, "pos_y": 0.77
        },
    ]
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 장치 노드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DeviceNode(QGraphicsRectItem):
    NODE_W = 175
    NODE_H = 105

    def __init__(self, device, device_type, scene_w, scene_h, on_click_cb):
        px = device['pos_x'] * scene_w - self.NODE_W / 2
        py = device['pos_y'] * scene_h - self.NODE_H / 2
        super().__init__(px, py, self.NODE_W, self.NODE_H)
        self.device = device
        self.device_type = device_type
        self.scene_w = scene_w
        self.scene_h = scene_h
        self.on_click_cb = on_click_cb
        self._base_color = QColor(C_HP if device_type == 'heatpump' else C_GP)
        self._hover = False
        self._dragging = False
        self._drag_start_pos = None  # 드래그 시작 씬 좌표
        self._drag_start_rect = None  # 드래그 시작 rect

        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setBrush(QBrush())

    def hoverEnterEvent(self, event):
        self._hover = True
        self.setZValue(10)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover = False
        if not self._dragging:
            self.setZValue(1)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_start_pos = event.scenePos()
            self._drag_start_rect = self.pos()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self.setZValue(20)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None:
            delta = event.scenePos() - self._drag_start_pos
            if delta.manhattanLength() > 3:
                self._dragging = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            self.setZValue(5)

            if self._dragging:
                center_x = self.pos().x() + self.rect().x() + self.NODE_W / 2
                center_y = self.pos().y() + self.rect().y() + self.NODE_H / 2
                self.device['pos_x'] = max(0.0, min(1.0, center_x / self.scene_w))
                self.device['pos_y'] = max(0.0, min(1.0, center_y / self.scene_h))
            else:
                self.on_click_cb(self.device, self.device_type)

            self._dragging = False
            self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        radius = 10.0

        # 배경 그라디언트
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        base = QColor(self._base_color)
        l = base.lighter(130 if self._hover else 115)
        d = base.darker(115)
        l.setAlpha(245); d.setAlpha(235)
        grad.setColorAt(0, l); grad.setColorAt(1, d)
        painter.fillPath(path, QBrush(grad))

        # 테두리
        border = base.darker(130) if self._hover else base.darker(110)
        painter.strokePath(path, QPen(border, 2.0 if self._hover else 1.5))

        # 장치명 (흰색)
        painter.setPen(QPen(QColor('#FFFFFF')))
        painter.setFont(QFont('Malgun Gothic', 11, QFont.Weight.Bold))
        painter.drawText(
            QRectF(r.left()+10, r.top()+8, r.width()-20, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.device['name']
        )

        # 구분선
        painter.setPen(QPen(QColor(255, 255, 255, 80), 1))
        painter.drawLine(int(r.left()+10), int(r.top()+34), int(r.right()-10), int(r.top()+34))

        # IP (밝은 노란빛)
        painter.setFont(QFont('Consolas', 9))
        painter.setPen(QPen(QColor(255, 255, 220)))
        painter.drawText(
            QRectF(r.left()+10, r.top()+38, r.width()-20, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"IP : {self.device['ip']}"
        )

        # Slave IDs (연한 흰색)
        sensors = self.device.get('sensors', {})
        t1 = sensors.get('temp1_slave_id', '-')
        t2 = sensors.get('temp2_slave_id', '-')
        fl = sensors.get('flow_slave_id', '-')
        painter.setFont(QFont('Consolas', 8))
        painter.setPen(QPen(QColor(230, 230, 255, 220)))
        painter.drawText(QRectF(r.left()+10, r.top()+58, r.width()-20, 16),
                         Qt.AlignmentFlag.AlignLeft, f"온도센서 {t1}, {t2}")
        painter.drawText(QRectF(r.left()+10, r.top()+76, r.width()-20, 16),
                         Qt.AlignmentFlag.AlignLeft, f"유량센서 {fl}")

        # 드래그 중 강조 테두리
        if self._dragging:
            gp = QPainterPath()
            gp.addRoundedRect(r.adjusted(1, 1, -1, -1), radius, radius)
            painter.strokePath(gp, QPen(QColor(255, 255, 255, 160), 3))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 휠 줌 지원 뷰
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ZoomableView(QGraphicsView):
    """마우스 휠 줌 + 빈 공간 드래그 이동"""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._zoom = 1.0
        self._panning = False
        self._pan_start = None
        self.setBackgroundBrush(QBrush(QColor('#f8f9fa')))

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = max(0.2, min(self._zoom * factor, 5.0))
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        # 노드 위에서 누른 경우 → 노드가 처리하도록 그냥 전달
        item = self.itemAt(event.pos())
        if item is not None:
            super().mousePressEvent(event)
            return
        # 빈 공간 → 뷰 패닝
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._panning:
            self._panning = False
            self._pan_start = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().mouseReleaseEvent(event)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 배치도 씬
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LayoutScene(QGraphicsScene):
    SCENE_W = 1380.0
    SCENE_H = 800.0

    def __init__(self, devices, on_device_click):
        super().__init__()
        self.setSceneRect(0, 0, self.SCENE_W, self.SCENE_H)
        self.devices = devices
        self.on_device_click = on_device_click
        self.device_nodes = []
        self._draw_bg()
        self._draw_devices()

    def _draw_bg(self):
        W, H = self.SCENE_W, self.SCENE_H

        # 흰색 배경
        bg = QGraphicsRectItem(0, 0, W, H)
        bg.setBrush(QBrush(QColor('#f8f9fa')))
        bg.setPen(QPen(Qt.PenStyle.NoPen))
        bg.setZValue(-10)
        self.addItem(bg)

        # 연한 그리드
        gp = QPen(QColor(0, 0, 0, 18), 1)
        for x in range(0, int(W), 60):
            self.addLine(x, 0, x, H, gp).setZValue(-9)
        for y in range(0, int(H), 60):
            self.addLine(0, y, W, y, gp).setZValue(-9)

        # 외곽 경계선
        outer = QGraphicsRectItem(10, 10, W-20, H-20)
        outer.setPen(QPen(QColor(C_PRIMARY), 2))
        outer.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        outer.setZValue(0)
        self.addItem(outer)

    def _zone(self, x, y, w, h, color_hex, label):
        c = QColor(color_hex)
        fill = QColor(c); fill.setAlpha(18)
        border = QColor(c); border.setAlpha(130)
        r = QGraphicsRectItem(x, y, w, h)
        r.setBrush(QBrush(fill))
        r.setPen(QPen(border, 1.5, Qt.PenStyle.DashLine))
        r.setZValue(1)
        self.addItem(r)
        self._lbl(label, x+7, y+7, color_hex, 8).setZValue(2)

    def _lbl(self, text, x, y, color, size=9):
        from PyQt6.QtWidgets import QGraphicsTextItem
        item = QGraphicsTextItem(text)
        item.setFont(QFont('Malgun Gothic', size))
        item.setDefaultTextColor(QColor(color))
        item.setPos(x, y)
        self.addItem(item)
        return item

    def _draw_devices(self):
        self.device_nodes.clear()
        for dev in self.devices.get('heatpump', []):
            n = DeviceNode(dev, 'heatpump', self.SCENE_W, self.SCENE_H, self.on_device_click)
            n.setZValue(5); self.addItem(n); self.device_nodes.append(n)
        for dev in self.devices.get('groundpipe', []):
            n = DeviceNode(dev, 'groundpipe', self.SCENE_W, self.SCENE_H, self.on_device_click)
            n.setZValue(5); self.addItem(n); self.device_nodes.append(n)

    def refresh_devices(self, devices):
        for n in self.device_nodes:
            self.removeItem(n)
        self.device_nodes.clear()
        self.devices = devices
        self._draw_devices()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 장치 편집 팝업
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DeviceEditDialog(QDialog):
    def __init__(self, device, device_type, parent=None):
        super().__init__(parent)
        self.device = dict(device)
        self.device_type = device_type
        color = C_HP if device_type == 'heatpump' else C_GP
        self.setWindowTitle(f'장치 설정 — {device["name"]}')
        self.setMinimumWidth(430)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {C_BG}; }}
            QLabel {{ color: {C_TEXT}; font-family: Malgun Gothic; }}
            QLineEdit, QSpinBox {{
                background-color: {C_BG2}; color: {C_TEXT};
                border: 1px solid {color}; border-radius: 6px;
                padding: 6px 10px; font-size: 12px;
            }}
            QGroupBox {{
                color: {color}; border: 1px solid {color}; border-radius: 8px;
                margin-top: 14px; font-weight: bold;
                font-family: Malgun Gothic; font-size: 11px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
            QPushButton {{
                background-color: {C_BG2}; color: {C_TEXT};
                border: 1px solid {color}; border-radius: 6px;
                padding: 8px 20px; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {color}; color: #fff; }}
            QCheckBox {{ color: {color}; font-family: Malgun Gothic; }}
        """)
        self._build(color)

    def _build(self, color):
        layout = QVBoxLayout()
        layout.setSpacing(14); layout.setContentsMargins(22, 22, 22, 22)

        hdr = QLabel(f'🔧 {self.device["name"]} 설정')
        hdr.setFont(QFont('Malgun Gothic', 13, QFont.Weight.Bold))
        hdr.setStyleSheet(f'color: {color};')
        layout.addWidget(hdr)

        # 기본 정보
        basic = QGroupBox('기본 정보')
        basic.setFont(QFont('Malgun Gothic', 10))
        form = QFormLayout(); form.setSpacing(10)
        self.name_edit = QLineEdit(self.device['name'])
        self.ip_edit   = QLineEdit(self.device['ip'])
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.device.get('port', 8899))
        self.desc_edit = QLineEdit(self.device.get('description', ''))
        self.enabled_chk = QCheckBox('활성화')
        self.enabled_chk.setChecked(self.device.get('enabled', True))
        form.addRow('장치명:', self.name_edit)
        form.addRow('IP 주소:', self.ip_edit)
        form.addRow('포트:', self.port_spin)
        form.addRow('설명:', self.desc_edit)
        form.addRow('', self.enabled_chk)
        basic.setLayout(form)
        layout.addWidget(basic)

        # Slave ID
        slave = QGroupBox('센서 Slave ID')
        slave.setFont(QFont('Malgun Gothic', 10))
        sform = QFormLayout(); sform.setSpacing(10)
        sensors = self.device.get('sensors', {})
        self.t1 = QSpinBox(); self.t1.setRange(1, 255); self.t1.setValue(sensors.get('temp1_slave_id', 1))
        self.t2 = QSpinBox(); self.t2.setRange(1, 255); self.t2.setValue(sensors.get('temp2_slave_id', 2))
        self.fl = QSpinBox(); self.fl.setRange(1, 255); self.fl.setValue(sensors.get('flow_slave_id', 3))
        sform.addRow('온도센서 1 (입구) Slave ID:', self.t1)
        sform.addRow('온도센서 2 (출구) Slave ID:', self.t2)
        sform.addRow('유량센서 Slave ID:', self.fl)
        slave.setLayout(sform)
        layout.addWidget(slave)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText('💾 저장')
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText('✗ 취소')
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        self.setLayout(layout)

    def _on_save(self):
        ip = self.ip_edit.text().strip()
        parts = ip.split('.')
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            QMessageBox.warning(self, '입력 오류', '올바른 IP 주소를 입력해주세요.\n예) 172.30.1.97')
            return
        self.device.update({
            'name':        self.name_edit.text().strip(),
            'ip':          ip,
            'port':        self.port_spin.value(),
            'description': self.desc_edit.text().strip(),
            'enabled':     self.enabled_chk.isChecked(),
            'sensors': {
                'temp1_slave_id': self.t1.value(),
                'temp2_slave_id': self.t2.value(),
                'flow_slave_id':  self.fl.value(),
            }
        })
        self.accept()

    def get_device(self):
        return self.device


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 장치 추가 다이얼로그
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AddDeviceDialog(QDialog):
    def __init__(self, existing_ids, parent=None):
        super().__init__(parent)
        self.existing_ids = existing_ids
        self.setWindowTitle('장치 추가')
        self.setMinimumWidth(400)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {C_BG}; }}
            QLabel {{ color: {C_TEXT}; font-family: Malgun Gothic; }}
            QLineEdit, QSpinBox, QComboBox {{
                background-color: {C_BG2}; color: {C_TEXT};
                border: 1px solid {C_PRIMARY}; border-radius: 6px; padding: 6px 10px;
            }}
            QPushButton {{
                background-color: {C_BG2}; color: {C_TEXT};
                border: 1px solid {C_PRIMARY}; border-radius: 6px; padding: 8px 20px;
            }}
            QPushButton:hover {{ background-color: {C_PRIMARY}; color: #fff; }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(); layout.setSpacing(14); layout.setContentsMargins(22, 22, 22, 22)
        t = QLabel('➕ 새 장치 추가')
        t.setFont(QFont('Malgun Gothic', 13, QFont.Weight.Bold))
        t.setStyleSheet(f'color: {C_PRIMARY};')
        layout.addWidget(t)

        form = QFormLayout(); form.setSpacing(10)
        self.type_combo = QComboBox(); self.type_combo.addItems(['히트펌프', '지중배관'])
        self.id_edit   = QLineEdit(); self.id_edit.setPlaceholderText('예) HP_5')
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText('예) 히트펌프_5')
        self.ip_edit   = QLineEdit(); self.ip_edit.setPlaceholderText('예) 172.30.1.106')
        self.port_spin = QSpinBox(); self.port_spin.setRange(1, 65535); self.port_spin.setValue(8899)
        self.t1 = QSpinBox(); self.t1.setRange(1, 255); self.t1.setValue(1)
        self.t2 = QSpinBox(); self.t2.setRange(1, 255); self.t2.setValue(2)
        self.fl = QSpinBox(); self.fl.setRange(1, 255); self.fl.setValue(3)
        form.addRow('장치 타입:', self.type_combo)
        form.addRow('Device ID:', self.id_edit)
        form.addRow('장치명:', self.name_edit)
        form.addRow('IP 주소:', self.ip_edit)
        form.addRow('포트:', self.port_spin)
        form.addRow('온도센서 1 Slave ID:', self.t1)
        form.addRow('온도센서 2 Slave ID:', self.t2)
        form.addRow('유량센서 Slave ID:', self.fl)
        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText('➕ 추가')
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText('✗ 취소')
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        self.setLayout(layout)

    def _on_ok(self):
        did, name, ip = (self.id_edit.text().strip(),
                         self.name_edit.text().strip(),
                         self.ip_edit.text().strip())
        if not did or not name or not ip:
            QMessageBox.warning(self, '입력 오류', 'Device ID, 장치명, IP를 모두 입력해주세요.'); return
        if did in self.existing_ids:
            QMessageBox.warning(self, '중복 오류', f'이미 존재하는 Device ID: {did}'); return
        parts = ip.split('.')
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            QMessageBox.warning(self, '입력 오류', '올바른 IP 주소를 입력해주세요.'); return
        self.accept()

    def get_device_type(self):
        return 'heatpump' if self.type_combo.currentText() == '히트펌프' else 'groundpipe'

    def get_device(self):
        return {
            'device_id': self.id_edit.text().strip(),
            'name':      self.name_edit.text().strip(),
            'ip':        self.ip_edit.text().strip(),
            'port':      self.port_spin.value(),
            'description': '',
            'enabled':   True,
            'sensors': {
                'temp1_slave_id': self.t1.value(),
                'temp2_slave_id': self.t2.value(),
                'flow_slave_id':  self.fl.value(),
            },
            'pos_x': 0.48,
            'pos_y': 0.48,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 배치도 다이얼로그
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LayoutMapDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('🏭 공장 센서 배치도')
        self.setMinimumSize(1280, 780)

        self.config_file = Path('config/box_ips.json')
        self.devices = self._load_devices()

        self.setStyleSheet(f"""
            QDialog {{ background-color: {C_BG}; }}
            QLabel  {{ color: {C_TEXT}; }}
            QPushButton {{
                background-color: {C_BG2}; color: {C_TEXT};
                border: 1px solid {C_PRIMARY}; border-radius: 6px;
                padding: 7px 16px; font-size: 11px; font-family: Malgun Gothic;
            }}
            QPushButton:hover {{ background-color: {C_PRIMARY}; color: #fff; }}
        """)
        self._build_ui()

    def _load_devices(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._merge_pos(data)
                return data
        except Exception as e:
            logger.error(f"배치도 로드 실패: {e}")
        return {k: [dict(d) for d in v] for k, v in DEFAULT_DEVICES.items()}

    def _merge_pos(self, data):
        def_hp = {d['device_id']: d for d in DEFAULT_DEVICES['heatpump']}
        def_gp = {d['device_id']: d for d in DEFAULT_DEVICES['groundpipe']}
        for dev in data.get('heatpump', []):
            if 'pos_x' not in dev:
                ref = def_hp.get(dev['device_id'], {})
                dev['pos_x'] = ref.get('pos_x', 0.5)
                dev['pos_y'] = ref.get('pos_y', 0.5)
        for dev in data.get('groundpipe', []):
            if 'pos_x' not in dev:
                ref = def_gp.get(dev['device_id'], {})
                dev['pos_x'] = ref.get('pos_x', 0.5)
                dev['pos_y'] = ref.get('pos_y', 0.5)

    def _save_devices(self):
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            out = dict(self.devices)
            out['comment']      = '플라스틱 함 센서 IP 주소 및 Slave ID 설정'
            out['last_updated'] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"배치도 저장 실패: {e}")
            return False

    def _build_ui(self):
        main = QVBoxLayout(); main.setSpacing(10); main.setContentsMargins(16, 16, 16, 16)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel('🏭 공장 센서 배치도')
        title.setFont(QFont('Malgun Gothic', 16, QFont.Weight.Bold))
        title.setStyleSheet(f'color: {C_PRIMARY};')
        hdr.addWidget(title); hdr.addStretch()

        # 범례
        for dot_c, lbl_txt in [(C_HP, '히트펌프'), (C_GP, '지중배관')]:
            dot = QLabel('●'); dot.setStyleSheet(f'color:{dot_c}; font-size:15px;')
            lbl = QLabel(lbl_txt); lbl.setFont(QFont('Malgun Gothic', 10))
            hdr.addWidget(dot); hdr.addWidget(lbl); hdr.addSpacing(10)
        hdr.addSpacing(12)

        # 버튼
        add_btn = QPushButton('➕ 장치 추가'); add_btn.clicked.connect(self._on_add)

        del_btn = QPushButton('🗑 장치 삭제')
        del_btn.setStyleSheet(f"""
            QPushButton {{ background-color:{C_BG2}; color:{C_TEXT};
                border:1px solid {C_DANGER}; border-radius:6px; padding:7px 16px; }}
            QPushButton:hover {{ background-color:{C_DANGER}; color:white; }}""")
        del_btn.clicked.connect(self._on_delete)

        save_btn = QPushButton('💾 저장')
        save_btn.setStyleSheet(f"""
            QPushButton {{ background-color:{C_SUCCESS}; color:#fff; border:none;
                border-radius:6px; padding:7px 20px; font-weight:bold; }}
            QPushButton:hover {{ background-color:#2e7d32; }}""")
        save_btn.clicked.connect(self._on_save)

        close_btn = QPushButton('✗ 닫기'); close_btn.clicked.connect(self.reject)

        for b in [add_btn, del_btn, save_btn, close_btn]:
            hdr.addWidget(b)
        main.addLayout(hdr)

        # 힌트
        hint = QLabel('💡 장치를 드래그하여 위치 이동  |  클릭하면 IP / 포트 / Slave ID 수정  |  저장 시 위치가 함께 저장됩니다.')
        hint.setFont(QFont('Malgun Gothic', 9))
        hint.setStyleSheet(f'color: {C_TEXT2};')
        main.addWidget(hint)

        # 씬 & 뷰
        self.scene = LayoutScene(self.devices, self._on_device_click)
        self.view  = ZoomableView(self.scene)
        self.view.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setStyleSheet(f'border:1px solid {C_BORDER}; border-radius:8px; background-color:#f8f9fa;')
        self.view.setMinimumHeight(580)
        main.addWidget(self.view, stretch=1)

        # 상태바
        status_row = QHBoxLayout()
        hp_n = len(self.devices.get('heatpump', []))
        gp_n = len(self.devices.get('groundpipe', []))
        self.status_lbl = QLabel(
            f'히트펌프 {hp_n}개  |  지중배관 {gp_n}개  |  총 {hp_n+gp_n}개 장치')
        self.status_lbl.setFont(QFont('Malgun Gothic', 9))
        self.status_lbl.setStyleSheet(f'color: {C_TEXT2};')
        status_row.addWidget(self.status_lbl); status_row.addStretch()
        zh = QLabel('🔍 휠: 확대/축소  |  빈 공간 드래그: 이동')
        zh.setFont(QFont('Malgun Gothic', 9)); zh.setStyleSheet(f'color: {C_TEXT2};')
        status_row.addWidget(zh)
        main.addLayout(status_row)
        self.setLayout(main)

    def showEvent(self, event):
        """창이 표시될 때 씬에 맞게 뷰 조정"""
        super().showEvent(event)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'view'):
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        """다이얼로그 레벨 휠 이벤트 - 뷰로 전달"""
        pass

    def _on_device_click(self, device, device_type):
        dlg = DeviceEditDialog(device, device_type, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_device()
            lst = self.devices.get(device_type, [])
            for i, d in enumerate(lst):
                if d['device_id'] == device['device_id']:
                    updated['pos_x'] = d.get('pos_x', 0.5)
                    updated['pos_y'] = d.get('pos_y', 0.5)
                    updated['id']    = d.get('id', i+1)
                    lst[i] = updated
                    break
            self.devices[device_type] = lst
            self.scene.refresh_devices(self.devices)
            self._update_status()

    def _on_add(self):
        existing = ([d['device_id'] for d in self.devices.get('heatpump', [])] +
                    [d['device_id'] for d in self.devices.get('groundpipe', [])])
        dlg = AddDeviceDialog(existing, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dtype  = dlg.get_device_type()
            newdev = dlg.get_device()
            lst    = self.devices.get(dtype, [])
            newdev['id'] = len(lst)+1
            lst.append(newdev)
            self.devices[dtype] = lst
            self.scene.refresh_devices(self.devices)
            self._update_status()
            QMessageBox.information(self, '추가 완료',
                f"'{newdev['name']}' 장치가 추가되었습니다.\n"
                "배치도 중앙에 임시 배치되었습니다.\n저장 후 확인하세요.")

    def _on_delete(self):
        all_devs = ([(t, d) for t in ('heatpump', 'groundpipe')
                     for d in self.devices.get(t, [])])
        if not all_devs:
            QMessageBox.information(self, '알림', '삭제할 장치가 없습니다.'); return

        dlg = QDialog(self); dlg.setWindowTitle('장치 삭제'); dlg.setMinimumWidth(340)
        dlg.setStyleSheet(f"""
            QDialog {{ background-color:{C_BG}; }}
            QLabel  {{ color:{C_TEXT}; font-family:Malgun Gothic; }}
            QComboBox {{ background-color:{C_BG2}; color:{C_TEXT};
                border:1px solid {C_DANGER}; border-radius:6px; padding:6px 10px; }}
            QPushButton {{ background-color:{C_BG2}; color:{C_TEXT};
                border:1px solid {C_DANGER}; border-radius:6px; padding:8px 20px; }}
            QPushButton:hover {{ background-color:{C_DANGER}; color:white; }}""")
        dl = QVBoxLayout(); dl.setContentsMargins(20, 20, 20, 20); dl.setSpacing(14)
        lbl = QLabel('삭제할 장치를 선택하세요:')
        lbl.setFont(QFont('Malgun Gothic', 11)); dl.addWidget(lbl)
        combo = QComboBox()
        for dtype, dev in all_devs:
            kr = '히트펌프' if dtype == 'heatpump' else '지중배관'
            combo.addItem(f"[{kr}] {dev['name']}  ({dev['device_id']})")
        dl.addWidget(combo)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText('🗑 삭제')
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText('취소')
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        dl.addWidget(btns); dlg.setLayout(dl)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            dtype, dev = all_devs[combo.currentIndex()]
            if QMessageBox.question(
                self, '삭제 확인',
                f"'{dev['name']}' 장치를 삭제하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.devices[dtype] = [
                    d for d in self.devices[dtype]
                    if d['device_id'] != dev['device_id']]
                self.scene.refresh_devices(self.devices)
                self._update_status()

    def _on_save(self):
        if self._save_devices():
            QMessageBox.information(self, '저장 완료',
                '설정이 저장되었습니다.\n변경사항 적용을 위해 프로그램을 재시작하세요.')
        else:
            QMessageBox.critical(self, '저장 실패', '설정 파일 저장에 실패했습니다.')

    def _update_status(self):
        hp_n = len(self.devices.get('heatpump', []))
        gp_n = len(self.devices.get('groundpipe', []))
        self.status_lbl.setText(
            f'히트펌프 {hp_n}개  |  지중배관 {gp_n}개  |  총 {hp_n+gp_n}개 장치')