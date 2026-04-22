"""
grpoundpipe-260309.csv 데이터를 device_id별로 시각화하는 스크립트
- device_id: GP_1~4, GP_7~9
- 측정 항목: input_temp, output_temp, flow (3개 메트릭)
사용법: python groundpipe_chart.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings("ignore")

# ── 설정 ──────────────────────────────────────────────
CSV_PATH      = "grpoundpipe-260309.csv"
TIMESTAMP_FMT = "%Y-%m-%d %I:%M %p"

# device_id별 테마
DEVICE_THEMES = {
    "GP_1": {"color": "#34D399", "bg": "#030D08", "grid": "#0D2B1A", "accent": "#6EE7B7"},
    "GP_2": {"color": "#2DD4BF", "bg": "#030D0C", "grid": "#0D2B27", "accent": "#5EEAD4"},
    "GP_3": {"color": "#4ADE80", "bg": "#040D03", "grid": "#122B0D", "accent": "#86EFAC"},
    "GP_4": {"color": "#A3E635", "bg": "#060D03", "grid": "#1A2B0D", "accent": "#BEF264"},
    "GP_7": {"color": "#38BDF8", "bg": "#030B0D", "grid": "#0D222B", "accent": "#7DD3FC"},
    "GP_8": {"color": "#818CF8", "bg": "#05030D", "grid": "#130D2B", "accent": "#A5B4FC"},
    "GP_9": {"color": "#F472B6", "bg": "#0D030A", "grid": "#2B0D1E", "accent": "#F9A8D4"},
}
DEFAULT_THEME = {"color": "#AAAAAA", "bg": "#0F1117", "grid": "#2D2F3A", "accent": "#CCCCCC"}

# 측정 항목 정의 (3개)
METRICS = [
    {"col": "input_temp",  "label": "Input Temp (°C)",  "unit": "°C"},
    {"col": "output_temp", "label": "Output Temp (°C)", "unit": "°C"},
    {"col": "flow",        "label": "Flow",             "unit": ""},
]


# ── 데이터 로드 ───────────────────────────────────────
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, na_values=["NULL"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], format=TIMESTAMP_FMT)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ── 스타일 적용 ───────────────────────────────────────
def apply_style(ax, theme: dict, title: str = ""):
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


# ── device 하나의 3개 메트릭 차트 ────────────────────
def plot_device(df: pd.DataFrame, device_id: str):
    theme = DEVICE_THEMES.get(device_id, DEFAULT_THEME)
    sub_all = df[df["device_id"] == device_id]

    # 3개 메트릭 → 1행 3열 레이아웃
    fig, axes = plt.subplots(1, 3, figsize=(20, 5), facecolor="#070A14")
    fig.suptitle(
        f"Groundpipe  ·  {device_id}",
        color=theme["accent"], fontsize=16, fontweight="bold", y=1.02
    )

    if not sub_all.empty:
        period = (f"{sub_all['timestamp'].min().strftime('%Y-%m-%d %H:%M')}"
                  f"  →  {sub_all['timestamp'].max().strftime('%Y-%m-%d %H:%M')}")
        fig.text(0.5, 0.97, period, ha="center", fontsize=8, color="#6B7280")

    for ax, meta in zip(axes, METRICS):
        sub = sub_all.dropna(subset=[meta["col"]])
        apply_style(ax, theme, title=meta["label"])

        if not sub.empty:
            ax.plot(sub["timestamp"], sub[meta["col"]],
                    color=theme["color"], linewidth=0.9, alpha=0.9)
            ax.fill_between(sub["timestamp"], sub[meta["col"]],
                            color=theme["color"], alpha=0.13)

            # 최대·최소 마커
            idx_max = sub[meta["col"]].idxmax()
            idx_min = sub[meta["col"]].idxmin()
            ax.scatter(sub.loc[idx_max, "timestamp"], sub.loc[idx_max, meta["col"]],
                       color=theme["accent"], s=45, zorder=5,
                       edgecolors="white", linewidths=0.6)
            ax.scatter(sub.loc[idx_min, "timestamp"], sub.loc[idx_min, meta["col"]],
                       color="white", s=28, zorder=5, marker="v", alpha=0.75)

            # 통계
            stats = (f"avg {sub[meta['col']].mean():.2f}  |  "
                     f"max {sub[meta['col']].max():.2f}  |  "
                     f"min {sub[meta['col']].min():.2f}")
            ax.text(0.5, -0.18, stats, transform=ax.transAxes,
                    ha="center", fontsize=7.5, color="#6B7280")

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.set_ylabel(meta["unit"], fontsize=8)

    plt.tight_layout()
    out_file = f"chart_groundpipe_{device_id}.png"
    plt.savefig(out_file, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.show()
    print(f"  ✅  {out_file} 저장 완료")


# ── 전체 device 한 번에 ───────────────────────────────
def plot_all_devices(df: pd.DataFrame):
    devices = sorted(df["device_id"].unique())
    print(f"  device 목록: {devices}\n")
    for dev in devices:
        print(f"  📊  {dev} 차트 생성 중...")
        plot_device(df, dev)


# ── 메인 ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"📂  데이터 로드 중: {CSV_PATH}")
    df = load_data(CSV_PATH)
    print(f"   → {len(df):,}행  |  {df['timestamp'].min()} ~ {df['timestamp'].max()}\n")

    # 특정 device만 보려면:
    # plot_device(df, "GP_1")

    # 전체 한 번에:
    plot_all_devices(df)

    print("\n🎉  완료! 저장 파일: chart_groundpipe_<device_id>.png")