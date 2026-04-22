"""
heatpump-260309.csv 데이터를 device_id별로 시각화하는 스크립트
사용법: python heatpump_chart.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings("ignore")

# ── 설정 ──────────────────────────────────────────────
CSV_PATH = "heatpump-260309.csv"   # 파일 경로 (필요시 수정)
TIMESTAMP_FMT = "%Y-%m-%d %I:%M %p"

# device_id별 고유 색상 및 테마
DEVICE_THEMES = {
    "HP_1": {
        "color":      "#00C9A7",   # 민트 그린
        "bg":         "#030D0A",
        "grid":       "#0D2B24",
        "accent":     "#00FFC8",
        "fill_alpha": 0.15,
    },
    "HP_2": {
        "color":      "#4E9AF1",   # 스카이 블루
        "bg":         "#030812",
        "grid":       "#0D1E3A",
        "accent":     "#82C4FF",
        "fill_alpha": 0.15,
    },
    "HP_3": {
        "color":      "#F7B731",   # 앰버 옐로우
        "bg":         "#0D0A03",
        "grid":       "#2B2110",
        "accent":     "#FFD97A",
        "fill_alpha": 0.13,
    },
    "HP_4": {
        "color":      "#FF6B6B",   # 코랄 레드
        "bg":         "#0D0305",
        "grid":       "#2B0D10",
        "accent":     "#FF9999",
        "fill_alpha": 0.13,
    },
}

# 측정 항목 정의
METRICS = [
    {"col": "input_temp",  "label": "Input Temp (°C)",  "unit": "°C"},
    {"col": "output_temp", "label": "Output Temp (°C)", "unit": "°C"},
    {"col": "flow",        "label": "Flow",             "unit": ""},
    {"col": "energy",      "label": "Energy (kWh)",     "unit": "kWh"},
]


# ── 데이터 로드 ───────────────────────────────────────
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, na_values=["NULL"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], format=TIMESTAMP_FMT)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ── device별 스타일 적용 ──────────────────────────────
def apply_device_style(ax, theme: dict, title: str = ""):
    ax.set_facecolor(theme["bg"])
    ax.tick_params(colors="#9CA3AF", labelsize=8)
    ax.xaxis.label.set_color("#9CA3AF")
    ax.yaxis.label.set_color("#9CA3AF")
    for spine in ax.spines.values():
        spine.set_edgecolor(theme["grid"])
    ax.grid(axis="y", color=theme["grid"], linewidth=0.5, linestyle="--", alpha=0.8)
    ax.grid(axis="x", color=theme["grid"], linewidth=0.3, linestyle=":", alpha=0.5)
    if title:
        ax.set_title(title, color=theme["accent"], fontsize=10, fontweight="bold", pad=8)


# ── device_id 하나의 4개 메트릭 차트 ─────────────────
def plot_device(df: pd.DataFrame, device_id: str):
    theme = DEVICE_THEMES.get(device_id, {
        "color": "#AAAAAA", "bg": "#0F1117", "grid": "#2D2F3A",
        "accent": "#CCCCCC", "fill_alpha": 0.12,
    })
    sub_all = df[df["device_id"] == device_id]

    fig = plt.figure(figsize=(18, 10), facecolor="#070A14")
    fig.suptitle(
        f"Heatpump  ·  {device_id}",
        color=theme["accent"], fontsize=18, fontweight="bold", y=0.98
    )

    # 기간 표시
    if not sub_all.empty:
        period = (f"{sub_all['timestamp'].min().strftime('%Y-%m-%d %H:%M')}"
                  f"  →  {sub_all['timestamp'].max().strftime('%Y-%m-%d %H:%M')}")
        fig.text(0.5, 0.94, period, ha="center", fontsize=9, color="#6B7280")

    gs = GridSpec(2, 2, figure=fig, hspace=0.5, wspace=0.3)

    for idx, meta in enumerate(METRICS):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])
        sub = sub_all.dropna(subset=[meta["col"]])

        apply_device_style(ax, theme, title=meta["label"])

        if not sub.empty:
            ax.plot(sub["timestamp"], sub[meta["col"]],
                    color=theme["color"], linewidth=0.9, alpha=0.9)
            ax.fill_between(sub["timestamp"], sub[meta["col"]],
                            color=theme["color"], alpha=theme["fill_alpha"])

            # 최대·최소 마커
            idx_max = sub[meta["col"]].idxmax()
            idx_min = sub[meta["col"]].idxmin()
            ax.scatter(sub.loc[idx_max, "timestamp"], sub.loc[idx_max, meta["col"]],
                       color=theme["accent"], s=45, zorder=5,
                       edgecolors="white", linewidths=0.6)
            ax.scatter(sub.loc[idx_min, "timestamp"], sub.loc[idx_min, meta["col"]],
                       color="white", s=28, zorder=5, marker="v", alpha=0.75)

            # 통계 텍스트
            stats = (f"avg {sub[meta['col']].mean():.2f}  |  "
                     f"max {sub[meta['col']].max():.2f}  |  "
                     f"min {sub[meta['col']].min():.2f}")
            ax.text(0.5, -0.22, stats, transform=ax.transAxes,
                    ha="center", fontsize=7.5, color="#6B7280")

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.set_ylabel(meta["unit"], fontsize=8)

    out_file = f"chart_{device_id}.png"
    plt.savefig(out_file, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.show()
    print(f"✅  {out_file} 저장 완료")


# ── 전체 device 한 번에 ───────────────────────────────
def plot_all_devices(df: pd.DataFrame):
    for dev in sorted(df["device_id"].unique()):
        print(f"📊  {dev} 차트 생성 중...")
        plot_device(df, dev)


# ── 메인 ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"📂  데이터 로드 중: {CSV_PATH}")
    df = load_data(CSV_PATH)
    print(f"   → {len(df):,}행 로드 완료  |  기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    print(f"   → device_id: {sorted(df['device_id'].unique())}\n")

    # ── 특정 device 하나만 보려면 ──
    # plot_device(df, "HP_1")

    # ── 전체 device 차트 한 번에 생성 ──
    plot_all_devices(df)

    print("\n🎉  모든 차트 생성 완료!")
    print("    저장 파일: chart_HP_1.png / chart_HP_2.png / chart_HP_3.png / chart_HP_4.png")