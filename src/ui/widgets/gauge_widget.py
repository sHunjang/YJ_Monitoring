# ==============================================
# 게이지 바 위젯
# ==============================================
"""
센서 값을 게이지 바로 표시하는 위젯
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient

from ui.theme import Theme


class GaugeBar(QWidget):
    """단일 게이지 바 위젯"""

    def __init__(self, label: str, unit: str = '', min_val: float = 0, max_val: float = 100,
                 color: str = None, parent=None):
        super().__init__(parent)
        self.label = label
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.color = color or Theme.PRIMARY
        self._value = 0.0
        self.setFixedHeight(52)
        self._build()

    def _build(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(3)

        # 상단: 라벨 + 값
        top = QHBoxLayout()
        self.label_widget = QLabel(self.label)
        self.label_widget.setFont(Theme.font(9))
        self.label_widget.setStyleSheet(f'color: {Theme.TEXT_SECONDARY};')
        top.addWidget(self.label_widget)
        top.addStretch()
        self.value_label = QLabel('--')
        self.value_label.setFont(Theme.font(10, bold=True))
        self.value_label.setStyleSheet(f'color: {self.color};')
        top.addWidget(self.value_label)
        layout.addLayout(top)

        # 게이지 바
        self.bar_widget = _GaugeBarCanvas(self.color, self.min_val, self.max_val)
        self.bar_widget.setFixedHeight(10)
        layout.addWidget(self.bar_widget)

        # 하단: min/max
        bot = QHBoxLayout()
        min_lbl = QLabel(f'{self.min_val}{self.unit}')
        min_lbl.setFont(Theme.font(8))
        min_lbl.setStyleSheet(f'color: {Theme.TEXT_SECONDARY};')
        max_lbl = QLabel(f'{self.max_val}{self.unit}')
        max_lbl.setFont(Theme.font(8))
        max_lbl.setStyleSheet(f'color: {Theme.TEXT_SECONDARY};')
        bot.addWidget(min_lbl)
        bot.addStretch()
        bot.addWidget(max_lbl)
        layout.addLayout(bot)

        self.setLayout(layout)

    def update_value(self, value: float):
        self._value = value
        self.value_label.setText(f'{value:.1f}{self.unit}')
        self.bar_widget.update_value(value)

        # 색상 상태
        ratio = (value - self.min_val) / (self.max_val - self.min_val) if (self.max_val - self.min_val) else 0
        if ratio > 0.85:
            self.value_label.setStyleSheet(f'color: {Theme.DANGER};')
        elif ratio > 0.65:
            self.value_label.setStyleSheet(f'color: {Theme.WARNING};')
        else:
            self.value_label.setStyleSheet(f'color: {self.color};')


class _GaugeBarCanvas(QWidget):
    """게이지 바 캔버스 (내부용)"""

    def __init__(self, color: str, min_val: float, max_val: float, parent=None):
        super().__init__(parent)
        self.color = color
        self.min_val = min_val
        self.max_val = max_val
        self._value = min_val

    def update_value(self, value: float):
        self._value = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        # 배경
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(Theme.BORDER)))
        painter.drawRoundedRect(0, 0, w, h, r, r)

        # 채우기
        rng = self.max_val - self.min_val
        ratio = max(0.0, min(1.0, (self._value - self.min_val) / rng)) if rng else 0
        fill_w = int(w * ratio)
        if fill_w > 0:
            grad = QLinearGradient(0, 0, fill_w, 0)
            base = QColor(self.color)
            grad.setColorAt(0, base.lighter(120))
            grad.setColorAt(1, base)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(0, 0, fill_w, h, r, r)

        painter.end()


class GaugeGroup(QWidget):
    """여러 게이지 바를 묶는 그룹 위젯"""

    def __init__(self, title: str = '', parent=None):
        super().__init__(parent)
        self.title = title
        self.gauges = {}
        self._build()

    def _build(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
            }}
        """)
        self.layout_ = QVBoxLayout()
        self.layout_.setContentsMargins(16, 12, 16, 12)
        self.layout_.setSpacing(6)

        if self.title:
            title_lbl = QLabel(self.title)
            title_lbl.setFont(Theme.font(11, bold=True))
            title_lbl.setStyleSheet(f'color: {Theme.TEXT_PRIMARY}; border: none;')
            self.layout_.addWidget(title_lbl)

            divider = QWidget()
            divider.setFixedHeight(1)
            divider.setStyleSheet(f'background-color: {Theme.BORDER}; border: none;')
            self.layout_.addWidget(divider)

        self.setLayout(self.layout_)

    def add_gauge(self, key: str, label: str, unit: str = '',
                  min_val: float = 0, max_val: float = 100, color: str = None):
        gauge = GaugeBar(label, unit, min_val, max_val, color)
        self.layout_.addWidget(gauge)
        self.gauges[key] = gauge

    def update_gauge(self, key: str, value: float):
        if key in self.gauges:
            self.gauges[key].update_value(value)

    def clear_gauges(self):
        """게이지 전체 제거"""
        for key in list(self.gauges.keys()):
            widget = self.gauges.pop(key)
            self.layout_.removeWidget(widget)
            widget.deleteLater()