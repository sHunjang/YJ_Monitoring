# ==============================================
# COP 탭 위젯
# ==============================================
"""
히트펌프 COP (성능계수) 계산 및 시각화 탭

COP 계산 공식:
  - Q(kcal) = ΔT(°C) × 유량차분(L) ÷ 1000(ton) × 1000
  - COP = Q(kcal) / 860 / E(kWh)   (860 kcal = 1 kWh)
  - E(kWh) = elec.total_energy 최신값 - 최과거값 (1시간 누적 차분)

온도 처리:
  - 입구/출구 온도 각각 1시간 수집 데이터 평균 (센서 누락 대응)

전력량 매핑:
  - HP_1 → elec device_id='히트펌프_1'
  - HP_2 → elec device_id='히트펌프_2'
  - HP_3 → elec device_id='히트펌프_3'
  - HP_4 → elec device_id='히트펌프_4'
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import pyqtgraph as pg

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from ui.theme import Theme
from services.ui_data_service import UIDataService

logger = logging.getLogger(__name__)

# ── 매핑 ─────────────────────────────────────
HP_TO_ELEC = {
    'HP_1': '히트펌프_1',
    'HP_2': '히트펌프_2',
    'HP_3': '히트펌프_3',
    'HP_4': '히트펌프_4',
}

# ── 차트 색상 ─────────────────────────────────
COLOR_COP   = '#1976d2'
COLOR_T_IN  = '#e53935'
COLOR_T_OUT = '#fb8c00'
COLOR_POWER = '#8e24aa'
COLOR_FLOW  = '#00897b'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 요약 카드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class CopCard(QFrame):
    def __init__(self, title: str, value: str = '-', color: str = '#1976d2', parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid {color};
                border-left: 5px solid {color};
                border-radius: 8px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(86)

        lay = QVBoxLayout()
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(3)

        self._title = QLabel(title)
        self._title.setFont(QFont('Malgun Gothic', 9))
        self._title.setStyleSheet(f'color: {color}; border: none;')

        self._value = QLabel(value)
        self._value.setFont(QFont('Malgun Gothic', 17, QFont.Weight.Bold))
        self._value.setStyleSheet('color: #212121; border: none;')
        self._value.setAlignment(Qt.AlignmentFlag.AlignLeft)

        lay.addWidget(self._title)
        lay.addWidget(self._value)
        self.setLayout(lay)

    def update_value(self, v: str):
        self._value.setText(v)

    def set_alert(self, on: bool):
        self._value.setStyleSheet(
            f'color: {"#c0392b" if on else "#212121"}; border: none;'
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 인터랙티브 멀티 라인 차트 (pyqtgraph 기반)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class CopMultiChart(QWidget):
    """
    여러 시계열을 겹쳐 표시.
    클릭 시 하단 정보 바에 해당 시각의 각 값을 표시.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        pg.setConfigOptions(antialias=True, foreground='#424242', background='w')
        self._series: Dict[str, Dict] = {}
        self._vline: Optional[pg.InfiniteLine] = None
        self._build()

    def _build(self):
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # 범례 행
        self._legend_row = QHBoxLayout()
        self._legend_row.setSpacing(16)
        self._legend_row.addStretch()
        root.addLayout(self._legend_row)

        # PlotWidget (x축: 시간)
        axis = pg.DateAxisItem(orientation='bottom')
        self._plot = pg.PlotWidget(axisItems={'bottom': axis})
        self._plot.setMinimumHeight(320)
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.getPlotItem().setLabel('bottom', '시각')
        self._plot.getPlotItem().setLabel('left', '값')
        self._plot.scene().sigMouseClicked.connect(self._on_click)
        root.addWidget(self._plot)

        # 클릭 정보 바
        self._info_bar = QFrame()
        self._info_bar.setStyleSheet(
            'QFrame { background:#fafafa; border:1px solid #e0e0e0; border-radius:6px; }'
        )
        self._info_bar.setFixedHeight(36)
        self._info_lay = QHBoxLayout()
        self._info_lay.setContentsMargins(12, 0, 12, 0)
        self._info_lay.setSpacing(20)
        self._info_bar.setLayout(self._info_lay)

        self._hint_lbl = QLabel('💡 그래프를 클릭하면 해당 시각의 값이 표시됩니다.')
        self._hint_lbl.setFont(QFont('Malgun Gothic', 9))
        self._hint_lbl.setStyleSheet('color:#bdbdbd; background:transparent; border:none;')
        self._info_lay.addWidget(self._hint_lbl)
        self._info_lay.addStretch()

        root.addWidget(self._info_bar)
        self.setLayout(root)

    # ── 외부 API ────────────────────────────────
    def clear(self):
        self._plot.clear()
        self._series.clear()
        self._vline = None

        # 범례 초기화
        while self._legend_row.count():
            item = self._legend_row.takeAt(0)
            if w := item.widget():
                w.deleteLater()
        self._legend_row.addStretch()

        # 정보 바 초기화
        while self._info_lay.count():
            item = self._info_lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()
        self._hint_lbl = QLabel('💡 그래프를 클릭하면 해당 시각의 값이 표시됩니다.')
        self._hint_lbl.setFont(QFont('Malgun Gothic', 9))
        self._hint_lbl.setStyleSheet('color:#bdbdbd; background:transparent; border:none;')
        self._info_lay.addWidget(self._hint_lbl)
        self._info_lay.addStretch()

    def add_series(
        self,
        key: str,
        timestamps: List[datetime],
        values: List[float],
        color: str,
        name: str,
        width: int = 2,
        dashed: bool = False,
    ):
        x = [ts.timestamp() for ts in timestamps]
        y = list(values)

        pen = pg.mkPen(
            color=QColor(color),
            width=width,
            style=Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine,
        )
        curve = self._plot.plot(x, y, pen=pen)
        self._series[key] = {
            'x': x, 'y': y,
            'color': color, 'name': name,
            'curve': curve,
        }

        # 범례: ● + 이름
        cnt = self._legend_row.count()   # 마지막이 stretch
        dot = QLabel('●')
        dot.setFont(QFont('Arial', 11))
        dot.setStyleSheet(f'color:{color}; border:none; background:transparent;')
        lbl = QLabel(name)
        lbl.setFont(QFont('Malgun Gothic', 9))
        lbl.setStyleSheet('color:#424242; border:none; background:transparent;')
        self._legend_row.insertWidget(cnt - 1, dot)
        self._legend_row.insertWidget(cnt,     lbl)

    # ── 클릭 핸들러 ─────────────────────────────
    def _on_click(self, event):
        if not self._series:
            return

        pos = event.scenePos()
        vb = self._plot.getPlotItem().getViewBox()
        if not vb.sceneBoundingRect().contains(pos):
            return

        clicked_x = vb.mapSceneToView(pos).x()
        clicked_dt = datetime.fromtimestamp(clicked_x)

        # 수직 보조선
        if self._vline:
            self._plot.removeItem(self._vline)
        self._vline = pg.InfiniteLine(
            pos=clicked_x, angle=90,
            pen=pg.mkPen('#bdbdbd', width=1, style=Qt.PenStyle.DashLine),
        )
        self._plot.addItem(self._vline)

        # 정보 바 갱신
        while self._info_lay.count():
            item = self._info_lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        # 시각 레이블
        time_lbl = QLabel(f'🕐 {clicked_dt.strftime("%m/%d %H:%M")}')
        time_lbl.setFont(QFont('Malgun Gothic', 9, QFont.Weight.Bold))
        time_lbl.setStyleSheet('color:#424242; background:transparent; border:none;')
        self._info_lay.addWidget(time_lbl)

        for key, s in self._series.items():
            if not s['x']:
                continue
            # 가장 가까운 인덱스
            idx = min(range(len(s['x'])), key=lambda i: abs(s['x'][i] - clicked_x))
            val = s['y'][idx]

            sep = QLabel('│')
            sep.setStyleSheet('color:#e0e0e0; background:transparent; border:none;')
            self._info_lay.addWidget(sep)

            dot = QLabel('■')
            dot.setFont(QFont('Arial', 10))
            dot.setStyleSheet(f'color:{s["color"]}; background:transparent; border:none;')
            self._info_lay.addWidget(dot)

            val_lbl = QLabel(f'{s["name"]}: <b>{val:.2f}</b>')
            val_lbl.setTextFormat(Qt.TextFormat.RichText)
            val_lbl.setFont(QFont('Malgun Gothic', 9))
            val_lbl.setStyleSheet('color:#424242; background:transparent; border:none;')
            self._info_lay.addWidget(val_lbl)

        self._info_lay.addStretch()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COP 탭 위젯 (메인)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class CopTabWidget(QWidget):
    HP_DEVICES = ['HP_1', 'HP_2', 'HP_3', 'HP_4']
    REFRESH_MS = 60_000

    def __init__(self, data_service: UIDataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(self.REFRESH_MS)
        self.refresh()

    # ─────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # 컨트롤
        ctrl = QHBoxLayout()

        dev_lbl = QLabel('장치 선택:')
        dev_lbl.setFont(QFont('Malgun Gothic', 12, QFont.Weight.Bold))
        dev_lbl.setStyleSheet('color:#212121;')
        ctrl.addWidget(dev_lbl)

        self.device_combo = QComboBox()
        self.device_combo.setFont(QFont('Malgun Gothic', 11))
        self.device_combo.setMinimumWidth(150)
        self.device_combo.addItems(self.HP_DEVICES)
        self.device_combo.currentTextChanged.connect(self.refresh)
        ctrl.addWidget(self.device_combo)

        ctrl.addSpacing(28)

        per_lbl = QLabel('조회 기간:')
        per_lbl.setFont(QFont('Malgun Gothic', 11))
        per_lbl.setStyleSheet('color:#555;')
        ctrl.addWidget(per_lbl)

        self.period_combo = QComboBox()
        self.period_combo.setFont(QFont('Malgun Gothic', 11))
        self.period_combo.setMinimumWidth(130)
        self.period_combo.addItems(['최근 24시간', '최근 48시간', '최근 7일'])
        self.period_combo.currentTextChanged.connect(self.refresh)
        ctrl.addWidget(self.period_combo)

        ctrl.addStretch()

        self.updated_lbl = QLabel('')
        self.updated_lbl.setFont(QFont('Malgun Gothic', 9))
        self.updated_lbl.setStyleSheet('color:#bdbdbd;')
        ctrl.addWidget(self.updated_lbl)

        root.addLayout(ctrl)

        # 카드 5개
        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_cop   = CopCard('최근 COP',    '-',       COLOR_COP)
        self.card_t_in  = CopCard('입구 온도',   '- °C',    COLOR_T_IN)
        self.card_t_out = CopCard('출구 온도',   '- °C',    COLOR_T_OUT)
        self.card_power = CopCard('소비 전력량', '- kWh',   COLOR_POWER)
        self.card_flow  = CopCard('유량',        '- L',     COLOR_FLOW)
        for c in [self.card_cop, self.card_t_in, self.card_t_out,
                  self.card_power, self.card_flow]:
            cards.addWidget(c)
        root.addLayout(cards)

        # 차트
        self.chart = CopMultiChart()
        root.addWidget(self.chart, stretch=1)

        # 공식
        formula = QLabel(
            'COP = Q(kcal) / 860 / E(kWh)   |   '
            'Q(kcal) = ΔT × 유량(L) ÷ 1000(ton) × 1000   |   '
            'ΔT = 입구온도 평균 − 출구온도 평균'
        )
        formula.setFont(QFont('Malgun Gothic', 8))
        formula.setStyleSheet('color:#bdbdbd;')
        root.addWidget(formula)

        self.setLayout(root)

    # ─────────────────────────────────────────────
    # 조회 기간
    # ─────────────────────────────────────────────
    def _get_hours(self) -> int:
        txt = self.period_combo.currentText()
        if '48' in txt: return 48
        if '7'  in txt: return 168
        return 24

    # ─────────────────────────────────────────────
    # 갱신
    # ─────────────────────────────────────────────
    def refresh(self):
        device_id = self.device_combo.currentText()
        if not device_id:
            return
        try:
            points = self._calc_cop_series(device_id, self._get_hours())
            self._update_cards(points)
            self._update_chart(points)
            self.updated_lbl.setText(f'갱신: {datetime.now().strftime("%H:%M:%S")}')
        except Exception as e:
            logger.error(f'COP 갱신 오류: {e}', exc_info=True)

    # ─────────────────────────────────────────────
    # COP 시계열 계산
    # ─────────────────────────────────────────────
    def _calc_cop_series(self, hp_device: str, total_hours: int) -> List[Dict]:
        """전체 기간 데이터를 한 번에 조회 후 슬롯별 계산"""
        elec_device = HP_TO_ELEC.get(hp_device)
        if not elec_device:
            return []

        now     = datetime.now()
        t_start = now - timedelta(hours=total_hours)

        # ── 전체 기간 데이터 1회 조회 (4쿼리) ──
        t_in_rows  = self.data_service.get_timeseries_heatpump_range(
            hp_device, t_start, now, 't_in')
        t_out_rows = self.data_service.get_timeseries_heatpump_range(
            hp_device, t_start, now, 't_out')
        flow_rows  = self.data_service.get_timeseries_heatpump_range(
            hp_device, t_start, now, 'flow')
        elec_rows  = self.data_service.get_timeseries_power_range(
            elec_device, t_start, now)

        if not t_in_rows or not t_out_rows or not flow_rows or not elec_rows:
            return []

        # ── Python에서 슬롯별 분리 ──────────────
        results = []
        for slot in range(total_hours):
            slot_end   = now - timedelta(hours=slot)
            slot_start = now - timedelta(hours=slot + 1)

            p = self._calc_one_slot_from_data(
                t_in_rows, t_out_rows, flow_rows, elec_rows,
                slot_start, slot_end
            )
            if p:
                results.append(p)

        results.sort(key=lambda x: x['timestamp'])
        return results


    def _calc_one_slot_from_data(
        self,
        t_in_rows: List[Dict],
        t_out_rows: List[Dict],
        flow_rows: List[Dict],
        elec_rows: List[Dict],
        t_start: datetime,
        t_end: datetime,
    ) -> Optional[Dict]:
        """미리 조회된 데이터에서 슬롯 범위만 필터링하여 COP 계산"""

        def _filter(rows):
            return [r for r in rows
                    if t_start <= r['timestamp'] <= t_end]

        s_in   = _filter(t_in_rows)
        s_out  = _filter(t_out_rows)
        s_flow = _filter(flow_rows)
        s_elec = _filter(elec_rows)

        if not s_in or not s_out:
            return None

        avg_t_in  = sum(r['value'] for r in s_in)  / len(s_in)
        avg_t_out = sum(r['value'] for r in s_out) / len(s_out)
        delta_t   = avg_t_in - avg_t_out

        if not s_flow or len(s_flow) < 2:
            return None
        flow_diff = s_flow[-1]['value'] - s_flow[0]['value']
        if flow_diff <= 0:
            return None

        if not s_elec or len(s_elec) < 2:
            return None
        power_kwh = s_elec[-1]['value'] - s_elec[0]['value']
        if power_kwh <= 0:
            return None

        heat_kcal = abs(delta_t) * (flow_diff / 1000) * 1000
        if heat_kcal <= 0:
            return None

        cop = heat_kcal / 860.0 / power_kwh

        return {
            'timestamp': t_start,
            'cop':       round(cop, 2),
            'avg_t_in':  round(avg_t_in, 2),
            'avg_t_out': round(avg_t_out, 2),
            'power_kwh': round(power_kwh, 3),
            'flow_diff': round(flow_diff, 1),
        }

    # ─────────────────────────────────────────────
    # 카드 업데이트
    # ─────────────────────────────────────────────
    def _update_cards(self, points: List[Dict]):
        if not points:
            self.card_cop.update_value('-')
            self.card_t_in.update_value('- °C')
            self.card_t_out.update_value('- °C')
            self.card_power.update_value('- kWh')
            self.card_flow.update_value('- L')
            return
        p = points[-1]
        self.card_cop.update_value(f"{p['cop']:.2f}")
        self.card_cop.set_alert(p['cop'] < 1.0)
        self.card_t_in.update_value(f"{p['avg_t_in']:.1f} °C")
        self.card_t_out.update_value(f"{p['avg_t_out']:.1f} °C")
        self.card_power.update_value(f"{p['power_kwh']:.3f} kWh")
        self.card_flow.update_value(f"{p['flow_diff']} L")

    # ─────────────────────────────────────────────
    # 차트 업데이트
    # ─────────────────────────────────────────────
    def _update_chart(self, points: List[Dict]):
        self.chart.clear()
        if not points:
            return
        ts = [p['timestamp'] for p in points]
        self.chart.add_series('cop',   ts, [p['cop']       for p in points], COLOR_COP,   'COP',         width=3)
        self.chart.add_series('t_in',  ts, [p['avg_t_in']  for p in points], COLOR_T_IN,  '입구온도(°C)', width=2)
        self.chart.add_series('t_out', ts, [p['avg_t_out'] for p in points], COLOR_T_OUT, '출구온도(°C)', width=2)
        self.chart.add_series('power', ts, [p['power_kwh'] for p in points], COLOR_POWER, '전력량(kWh)',  width=2, dashed=True)
        self.chart.add_series('flow',  ts, [p['flow_diff'] for p in points], COLOR_FLOW,  '유량(L)',      width=2, dashed=True)