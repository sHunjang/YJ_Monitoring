"""
elec-260309.csv 데이터를 device_id별로 시각화하는 스크립트
- device_id: Total, GP_1~6, HP_1~4
- 측정 항목: energy (단일 컬럼)
사용법: python elec_chart.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings("ignore")

# ── 설정 ──────────────────────────────────────────────
CSV_PATH   = "elec-260309.csv"
TIMESTAMP_FMT = "%Y-%m-%d %H:%M"

# device_id별 테마 (배경색 계열을 device 그룹으로 구분)
DEVICE_THEMES = {
    "Total": {"color": "#C084FC", "bg": "#08030D", "grid": "#1E0D2B", "accent": "#E0AAFF"},
    "GP_1":  {"color": "#34D399", "bg": "#030D08", "grid": "#0D2B1A", "accent": "#6EE7B7"},
    "GP_2":  {"color": "#2DD4BF", "bg": "#030D0C", "grid": "#0D2B27", "accent": "#5EEAD4"},
    "GP_3":  {"color": "#4ADE80", "bg": "#040D03", "grid": "#122B0D", "accent": "#86EFAC"},
    "GP_4":  {"color": "#A3E635", "bg": "#060D03", "grid": "#1A2B0D", "accent": "#BEF264"},
    "GP_5":  {"color": "#FACC15", "bg": "#0D0A03", "grid": "#2B2110", "accent": "#FDE68A"},
    "GP_6":  {"color": "#FB923C", "bg": "#0D0603", "grid": "#2B1610", "accent": "#FDBA74"},
    "HP_1":  {"color": "#00C9A7", "bg": "#030D0A", "grid": "#0D2B24", "accent": "#00FFC8"},
    "HP_2":  {"color": "#4E9AF1", "bg": "#030812", "grid": "#0D1E3A", "accent": "#82C4FF"},
    "HP_3":  {"color": "#F7B731", "bg": "#0D0A03", "grid": "#2B2110", "accent": "#FFD97A"},
    "HP_4":  {"color": "#FF6B6B", "bg": "#0D0305", "grid": "#2B0D10", "accent": "#FF9999"},
}
DEFAULT_THEME = {"color": "#AAAAAA", "bg": "#0F1117", "grid": "#2D2F3A", "accent": "#CCCCCC"}


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
        ax.set_title(title, color=theme["accent"], fontsize=11, fontweight="bold", pad=8)


# ── device 하나의 energy 시계열 차트 ─────────────────
def plot_device(df: pd.DataFrame, device_id: str):
    theme = DEVICE_THEMES.get(device_id, DEFAULT_THEME)
    sub = df[df["device_id"] == device_id].dropna(subset=["energy"])

    fig, ax = plt.subplots(figsize=(16, 5), facecolor="#070A14")
    fig.suptitle(
        f"Electricity  ·  {device_id}",
        color=theme["accent"], fontsize=16, fontweight="bold", y=1.01
    )

    if not sub.empty:
        period = (f"{sub['timestamp'].min().strftime('%Y-%m-%d %H:%M')}"
                  f"  →  {sub['timestamp'].max().strftime('%Y-%m-%d %H:%M')}")
        fig.text(0.5, 0.97, period, ha="center", fontsize=8, color="#6B7280")

        ax.plot(sub["timestamp"], sub["energy"],
                color=theme["color"], linewidth=0.9, alpha=0.9)
        ax.fill_between(sub["timestamp"], sub["energy"],
                        color=theme["color"], alpha=0.13)

        # 최대·최소 마커
        idx_max = sub["energy"].idxmax()
        idx_min = sub["energy"].idxmin()
        ax.scatter(sub.loc[idx_max, "timestamp"], sub.loc[idx_max, "energy"],
                   color=theme["accent"], s=50, zorder=5, edgecolors="white", linewidths=0.6)
        ax.scatter(sub.loc[idx_min, "timestamp"], sub.loc[idx_min, "energy"],
                   color="white", s=30, zorder=5, marker="v", alpha=0.75)

        # 통계
        stats = (f"avg {sub['energy'].mean():.2f}  |  "
                 f"max {sub['energy'].max():.2f}  |  "
                 f"min {sub['energy'].min():.2f}  |  "
                 f"count {len(sub):,}")
        ax.text(0.5, -0.13, stats, transform=ax.transAxes,
                ha="center", fontsize=8, color="#6B7280")

    apply_style(ax, theme, title="Energy (kWh)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.set_ylabel("kWh", fontsize=8)

    plt.tight_layout()
    out_file = f"chart_elec_{device_id}.png"
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
    # plot_device(df, "Total")
    # plot_device(df, "HP_1")

    # 전체 한 번에:
    plot_all_devices(df)

    print("\n🎉  완료! 저장 파일: chart_elec_<device_id>.png")