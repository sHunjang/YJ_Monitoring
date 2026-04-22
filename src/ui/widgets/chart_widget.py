# ==============================================
# 차트 위젯 (시각적 개선 버전)
# ==============================================
from datetime import datetime
from typing import List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import pyqtgraph as pg
from pyqtgraph import DateAxisItem

from ui.theme import Theme


class SmartDateAxisItem(DateAxisItem):
    def tickStrings(self, values, scale, spacing):
        if not values:
            return []
        time_range = max(values) - min(values)
        strings = []
        for value in values:
            try:
                dt = datetime.fromtimestamp(value)
                if time_range < 24 * 3600:
                    string = dt.strftime('%H:%M')
                elif time_range < 7 * 24 * 3600:
                    string = dt.strftime('%m-%d\n%H:%M')
                else:
                    string = dt.strftime('%m-%d')
                strings.append(string)
            except Exception:
                strings.append('')
        return strings


class PeriodButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(28)
        self.setFont(Theme.font(9))
        self._update_style(False)

    def setChecked(self, checked):
        super().setChecked(checked)
        self._update_style(checked)

    def _update_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.PRIMARY};
                    color: #ffffff;
                    border: 1px solid {Theme.PRIMARY};
                    border-radius: 5px;
                    padding: 0 12px;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.BG_SECONDARY};
                    color: {Theme.TEXT_SECONDARY};
                    border: 1px solid {Theme.BORDER};
                    border-radius: 5px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.BG_TERTIARY};
                    color: {Theme.PRIMARY};
                    border: 1px solid {Theme.PRIMARY};
                }}
            """)


class ChartWidget(QWidget):
    refresh_requested = pyqtSignal()
    time_range_changed = pyqtSignal(int)

    PERIOD_MAP = {
        '1시간':  1,
        '6시간':  6,
        '24시간': 24,
        '48시간': 48,
        '7일':    168,
    }

    def __init__(self, title='차트', parent=None):
        super().__init__(parent)
        self.title = title
        self.plot_lines = {}
        self.fill_items = {}
        self.line_colors = {}
        self.current_time_range = 1
        self.area_mode = False
        self.user_interacted = False
        self.tooltip_locked = False
        self.locked_tooltip_text = ''
        self.locked_tooltip_pos = (0, 0)
        self._init_ui()
        self._set_initial_x_range()

    def _init_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(12, 10, 12, 8)
        root.setSpacing(8)

        # 상단 컨트롤
        ctrl = QHBoxLayout()
        ctrl.setSpacing(6)

        title_lbl = QLabel(self.title)
        title_lbl.setFont(Theme.font(12, bold=True))
        title_lbl.setStyleSheet(f'color: {Theme.TEXT_PRIMARY};')
        ctrl.addWidget(title_lbl)
        ctrl.addStretch()

        # 기간 버튼
        self._period_group = QButtonGroup(self)
        self._period_group.setExclusive(True)
        self._period_btns = {}
        for p in ['1시간', '6시간', '24시간', '48시간', '7일']:
            btn = PeriodButton(p)
            self._period_btns[p] = btn
            self._period_group.addButton(btn)
            ctrl.addWidget(btn)
            btn.clicked.connect(lambda checked, period=p: self._on_period_clicked(period))
        self._period_btns['1시간'].setChecked(True)

        sep = QLabel('│')
        sep.setStyleSheet(f'color: {Theme.BORDER};')
        ctrl.addWidget(sep)

        # 라인/영역 전환
        self.line_btn = PeriodButton('라인')
        self.line_btn.setChecked(True)
        self.area_btn = PeriodButton('영역')
        self.line_btn.clicked.connect(lambda: self._set_area_mode(False))
        self.area_btn.clicked.connect(lambda: self._set_area_mode(True))
        ctrl.addWidget(self.line_btn)
        ctrl.addWidget(self.area_btn)

        sep2 = QLabel('│')
        sep2.setStyleSheet(f'color: {Theme.BORDER};')
        ctrl.addWidget(sep2)

        icon_style = f"""
            QPushButton {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: {Theme.BG_TERTIARY}; }}
        """
        refresh_btn = QPushButton('🔄')
        refresh_btn.setFont(Theme.font(10))
        refresh_btn.setFixedSize(30, 28)
        refresh_btn.setToolTip('새로고침')
        refresh_btn.setStyleSheet(icon_style)
        refresh_btn.clicked.connect(self._on_refresh)
        ctrl.addWidget(refresh_btn)

        auto_btn = QPushButton('⊡')
        auto_btn.setFont(Theme.font(10))
        auto_btn.setFixedSize(30, 28)
        auto_btn.setToolTip('자동 범위')
        auto_btn.setStyleSheet(icon_style)
        auto_btn.clicked.connect(self.auto_range)
        ctrl.addWidget(auto_btn)

        root.addLayout(ctrl)

        # 차트
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': SmartDateAxisItem()})
        self.plot_widget.setBackground(Theme.BG_SECONDARY)
        self.plot_widget.setMinimumHeight(240)

        axis_pen = pg.mkPen(color='#cccccc', width=1)
        for axis in ('bottom', 'left'):
            self.plot_widget.getAxis(axis).setPen(axis_pen)
            self.plot_widget.getAxis(axis).setTextPen(Theme.TEXT_SECONDARY)
            self.plot_widget.getAxis(axis).setStyle(tickLength=-6)

        left_axis = self.plot_widget.getAxis('left')
        left_axis.enableAutoSIPrefix(False)
        left_axis.tickStrings = lambda values, scale, spacing: [f'{v:.2f}' for v in values]

        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.legend = self.plot_widget.addLegend(
            offset=(10, 10),
            labelTextColor=Theme.TEXT_PRIMARY,
            brush=pg.mkBrush(color='#ffffffcc'),
            pen=pg.mkPen(color=Theme.BORDER, width=1)
        )
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.sigRangeChanged.connect(lambda: setattr(self, 'user_interacted', True))

        self.v_line = pg.InfiniteLine(angle=90, movable=False,
            pen=pg.mkPen('#bbbbbb', width=1, style=Qt.PenStyle.DashLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False,
            pen=pg.mkPen('#bbbbbb', width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)

        self._make_tooltip()

        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60, slot=self._on_mouse_moved
        )
        self.plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

        self.plot_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
            }}
        """)
        root.addWidget(self.plot_widget)

        # 하단 정보
        info = QHBoxLayout()
        self.info_label = QLabel('데이터 없음')
        self.info_label.setFont(Theme.font(9))
        self.info_label.setStyleSheet(f'color: {Theme.TEXT_SECONDARY};')
        info.addWidget(self.info_label)
        info.addStretch()
        self.cursor_label = QLabel('')
        self.cursor_label.setFont(Theme.font(9))
        self.cursor_label.setStyleSheet(f'color: {Theme.TEXT_SECONDARY};')
        info.addWidget(self.cursor_label)
        root.addLayout(info)

        self.setLayout(root)

    def _make_tooltip(self, locked=False):
        if hasattr(self, 'tooltip'):
            try:
                self.plot_widget.removeItem(self.tooltip)
            except Exception:
                pass
        self.tooltip = pg.TextItem(
            text='', anchor=(0, 1),
            color=Theme.TEXT_PRIMARY,
            fill=pg.mkBrush('#ffffffee'),
            border=pg.mkPen(Theme.WARNING if locked else Theme.BORDER,
                            width=3 if locked else 1)
        )
        self.tooltip.setFont(QFont(Theme.FONT_FAMILY, 9))
        self.plot_widget.addItem(self.tooltip)
        self.tooltip.setVisible(False)

    def _on_period_clicked(self, period):
        hours = self.PERIOD_MAP.get(period, 1)
        self.current_time_range = hours
        self._update_x_range()
        self.time_range_changed.emit(int(hours * 60))

    def _set_area_mode(self, area):
        self.area_mode = area
        self.line_btn.setChecked(not area)
        self.area_btn.setChecked(area)
        snapshot = {}
        for key, line in self.plot_lines.items():
            data = line.getData()
            if data[0] is not None and len(data[0]) > 0:
                snapshot[key] = (data[0], data[1],
                                 self.line_colors.get(key, Theme.PRIMARY), line.name())
        self.clear()
        for key, (xs, ys, color, name) in snapshot.items():
            pts = [{'timestamp': x, 'value': y} for x, y in zip(xs, ys)]
            self.add_line(key, pts, color=color, name=name)

    def _set_initial_x_range(self):
        now = datetime.now().timestamp()
        span = self.current_time_range * 3600
        self.plot_widget.setXRange(now - span, now, padding=0.02)

    def _update_x_range(self):
        latest = None
        for line in self.plot_lines.values():
            data = line.getData()
            if data[0] is not None and len(data[0]) > 0:
                t = max(data[0])
                if latest is None or t > latest:
                    latest = t
        if latest is None:
            latest = datetime.now().timestamp()
        span = self.current_time_range * 3600
        self.plot_widget.setXRange(latest - span, latest, padding=0.02)

    def _on_refresh(self):
        self.user_interacted = False
        self._set_initial_x_range()
        self.refresh_requested.emit()

    def _on_mouse_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.tooltip_locked = not self.tooltip_locked
            if self.tooltip_locked:
                if not self.tooltip.isVisible():
                    self.tooltip_locked = False
                    return
                self.locked_tooltip_text = self.tooltip.toPlainText()
                pos = self.tooltip.pos()
                self.locked_tooltip_pos = (pos.x(), pos.y())
                self._make_tooltip(locked=True)
                self.tooltip.setText(self.locked_tooltip_text)
                self.tooltip.setPos(*self.locked_tooltip_pos)
                self.tooltip.setVisible(True)
            else:
                self._make_tooltip(locked=False)

    def _on_mouse_moved(self, evt):
        if self.tooltip_locked:
            self.tooltip.setText(self.locked_tooltip_text)
            self.tooltip.setPos(*self.locked_tooltip_pos)
            self.tooltip.setVisible(True)
            return
        pos = evt[0]
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            self.tooltip.setVisible(False)
            return
        mp = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        x, y = mp.x(), mp.y()
        self.v_line.setPos(x)
        self.h_line.setPos(y)
        try:
            ts = datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S')
            self.cursor_label.setText(f'시간: {ts}  |  값: {y:.2f}')
        except Exception:
            self.cursor_label.setText('')

        closest_dist = float('inf')
        closest_x = closest_y = None
        closest_name = None
        vr = self.plot_widget.viewRange()
        xr = vr[0][1] - vr[0][0]
        yr = vr[1][1] - vr[1][0]

        for key, line in self.plot_lines.items():
            data = line.getData()
            if data[0] is None or len(data[0]) == 0:
                continue
            xs, ys = data[0], data[1]
            idx = min(range(len(xs)), key=lambda i: abs(xs[i] - x))
            xi, yi = xs[idx], ys[idx]
            if xr > 0 and yr > 0:
                d = ((xi - x) / xr) ** 2 + ((yi - y) / yr) ** 2
                if d < closest_dist:
                    closest_dist = d
                    closest_x, closest_y = xi, yi
                    closest_name = line.name()

        if closest_name and closest_dist < 0.003:
            ts2 = datetime.fromtimestamp(closest_x).strftime('%H:%M:%S')
            self.tooltip.setText(f'{closest_name}\n{ts2}\n{closest_y:.2f}')
            self.tooltip.setPos(closest_x, closest_y)
            self.tooltip.setVisible(True)
        else:
            self.tooltip.setVisible(False)

    def add_line(self, device_id, data, color=None, name=None, width=2):
        if not data:
            self._update_info()
            return
        if color is None:
            palette = [Theme.PRIMARY, Theme.HEATPUMP_COLOR, Theme.PIPE_COLOR,
                       Theme.WARNING, '#9c27b0', '#00bcd4', '#ff9800']
            color = palette[len(self.plot_lines) % len(palette)]
        if name is None:
            name = device_id
        self.line_colors[device_id] = color

        xs, ys = [], []
        for pt in data:
            ts = pt['timestamp']
            xs.append(ts.timestamp() if isinstance(ts, datetime) else ts)
            ys.append(pt['value'])

        if device_id in self.plot_lines:
            self.plot_widget.removeItem(self.plot_lines[device_id])
            del self.plot_lines[device_id]
        if device_id in self.fill_items:
            self.plot_widget.removeItem(self.fill_items[device_id])
            del self.fill_items[device_id]

        pen = pg.mkPen(color=color, width=width)
        line = self.plot_widget.plot(
            xs, ys, pen=pen, name=name,
            symbol='o', symbolSize=3, symbolBrush=color, symbolPen=None
        )
        self.plot_lines[device_id] = line

        if self.area_mode:
            fc = QColor(color)
            fc.setAlpha(40)
            baseline = self.plot_widget.plot(xs, [0]*len(xs), pen=None)
            fill = pg.FillBetweenItem(line, baseline, brush=pg.mkBrush(fc))
            self.plot_widget.addItem(fill)
            self.fill_items[device_id] = fill

        if not self.user_interacted:
            self._update_x_range()
            if ys:
                mn, mx = min(ys), max(ys)
                rng = mx - mn
                pad = rng * 0.15 if rng > 0.01 else max(abs((mn + mx) / 2) * 0.05, 0.5)
                self.plot_widget.setYRange(mn - pad, mx + pad, padding=0)
        self._update_info()

    def update_line(self, device_id, data):
        if device_id not in self.plot_lines or not data:
            return
        xs, ys = [], []
        for pt in data:
            ts = pt['timestamp']
            xs.append(ts.timestamp() if isinstance(ts, datetime) else ts)
            ys.append(pt['value'])
        self.plot_lines[device_id].setData(xs, ys)
        if not self.user_interacted:
            self._update_x_range()
            if ys:
                mn, mx = min(ys), max(ys)
                rng = mx - mn
                pad = rng * 0.15 if rng > 0.01 else max(abs((mn + mx) / 2) * 0.05, 0.5)
                self.plot_widget.setYRange(mn - pad, mx + pad, padding=0)
        self._update_info()

    def remove_line(self, device_id):
        if device_id in self.plot_lines:
            self.plot_widget.removeItem(self.plot_lines.pop(device_id))
        if device_id in self.fill_items:
            self.plot_widget.removeItem(self.fill_items.pop(device_id))
        self.line_colors.pop(device_id, None)
        self._update_info()

    def clear(self):
        for key in list(self.plot_lines.keys()):
            self.remove_line(key)
        self.plot_lines.clear()
        self.fill_items.clear()
        self.line_colors.clear()
        self.info_label.setText('데이터 없음')

    def set_labels(self, x_label=None, y_label=None):
        if x_label:
            self.plot_widget.setLabel('bottom', x_label, color=Theme.TEXT_SECONDARY)
        if y_label:
            self.plot_widget.setLabel('left', y_label, color=Theme.TEXT_SECONDARY)

    def auto_range(self):
        self.user_interacted = False
        self.plot_widget.autoRange()

    def _update_info(self):
        n = len(self.plot_lines)
        if n == 0:
            self.info_label.setText('데이터 없음')
        else:
            total = sum(
                len(l.getData()[0]) for l in self.plot_lines.values()
                if l.getData()[0] is not None
            )
            period = next(
                (p for p, btn in self._period_btns.items() if btn.isChecked()), '1시간'
            )
            self.info_label.setText(f'라인 {n}개  |  데이터 {total:,}건  |  {period}')
