import pandas as pd

# ─── 파일 경로 설정 ───────────────────────────────────────────
HEATPUMP_FILE = "sensor_exports/heatpump_HP_4_20260410_120601.csv"
POWER_FILE    = "sensor_exports/power_히트펌프_4_20260410_120702.csv"
OUTPUT_FILE   = "Heatpump_4.csv"
# ──────────────────────────────────────────────────────────────

ENCODING  = "utf-8-sig"
TIME_COL  = "측정시간"
TOLERANCE = pd.Timedelta("60s")

df_hp = pd.read_csv(HEATPUMP_FILE, encoding=ENCODING)
df_pw = pd.read_csv(POWER_FILE, encoding=ENCODING)

df_hp[TIME_COL] = pd.to_datetime(df_hp[TIME_COL])
df_pw[TIME_COL] = pd.to_datetime(df_pw[TIME_COL])

if "누적전력량(kWh)" in df_hp.columns:
    df_hp = df_hp.drop(columns=["누적전력량(kWh)"])

df_pw = df_pw.rename(columns={"누적전력량(kWh)": "누적전력량_전력계(kWh)"})

df_hp = df_hp.sort_values(TIME_COL).reset_index(drop=True)
df_pw = df_pw.sort_values(TIME_COL).reset_index(drop=True)

# heatpump → power 방향 매칭 (power 기준 행 보존을 위해 양쪽 다 처리)
left  = pd.merge_asof(df_hp, df_pw, on=TIME_COL, direction="nearest", tolerance=TOLERANCE)
right = pd.merge_asof(df_pw, df_hp, on=TIME_COL, direction="nearest", tolerance=TOLERANCE)

# power에만 있는 행 추출 (heatpump 컬럼이 전부 NaN인 행)
hp_cols = [c for c in df_hp.columns if c != TIME_COL]
only_in_power = right[right[hp_cols].isna().all(axis=1)].copy()

# 컬럼 순서 맞춰서 합치기
merged = pd.concat([left, only_in_power], ignore_index=True)
merged = merged.sort_values(TIME_COL).reset_index(drop=True)

merged.to_csv(OUTPUT_FILE, index=False, encoding=ENCODING)
print(f"완료: {len(merged)}행 → {OUTPUT_FILE}")
print(f"  heatpump 전용 행: {len(df_hp)}  |  power 전용 행: {len(only_in_power)}  |  합계: {len(merged)}")