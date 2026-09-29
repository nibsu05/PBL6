# ==============================================================================
# eda_visualization.py — Trực quan hóa dữ liệu (EDA) cho dự đoán mưa Đà Nẵng
# ==============================================================================
"""
Exploratory Data Analysis (EDA) — 8 biểu đồ chiến lược phục vụ bài toán
dự đoán lượng mưa cục bộ tại Đà Nẵng sử dụng Bi-LSTM & Informer.

Mỗi biểu đồ được thiết kế để trả lời một câu hỏi cụ thể về dữ liệu,
giúp đưa ra quyết định về feature selection, model design, và data preprocessing.

Biểu đồ:
  1. Phân bố lượng mưa (Target Distribution)
  2. Mùa vụ lượng mưa (Monthly Seasonality)
  3. Correlation Heatmap
  4. Multi-variable Time Series
  5. ENSO vs Rainfall
  6. Diurnal Pattern (chu kỳ trong ngày)
  7. Lag Correlation Analysis
  8. Feature Importance (Mutual Information)

Sử dụng:
  python eda_visualization.py

Output:
  eda_plots/  (thư mục chứa 8 file PNG)
"""

import os
import logging
import warnings

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Backend không cần GUI
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.ticker as ticker

from scipy import stats
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import StandardScaler

from config import (
    OPENMETEO_OUTPUT, ENSO_OUTPUT,
    ERA5_SST_OUTPUT, ERA5_PRESSURE_OUTPUT,
    TIMEZONE, START_YEAR, END_YEAR,
)

warnings.filterwarnings("ignore", category=FutureWarning)

# ==============================================================================
# CẤU HÌNH
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Thư mục output
from pathlib import Path
EDA_DIR = Path(__file__).resolve().parent / "eda_plots"
EDA_DIR.mkdir(parents=True, exist_ok=True)

# --- Style cấu hình toàn cục ---
plt.rcParams.update({
    "figure.facecolor": "#0D1117",
    "axes.facecolor": "#161B22",
    "axes.edgecolor": "#30363D",
    "axes.labelcolor": "#C9D1D9",
    "axes.titlepad": 14,
    "xtick.color": "#8B949E",
    "ytick.color": "#8B949E",
    "text.color": "#C9D1D9",
    "grid.color": "#21262D",
    "grid.alpha": 0.6,
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "figure.titlesize": 18,
    "legend.facecolor": "#161B22",
    "legend.edgecolor": "#30363D",
    "legend.fontsize": 9,
})

# Bảng màu chuyên dụng
COLORS = {
    "rain": "#58A6FF",
    "rain_heavy": "#F85149",
    "temperature": "#FFA657",
    "humidity": "#3FB950",
    "pressure": "#BC8CFF",
    "wind": "#79C0FF",
    "sst": "#FF7B72",
    "enso_el": "#F85149",
    "enso_la": "#58A6FF",
    "enso_neutral": "#8B949E",
    "accent1": "#D2A8FF",
    "accent2": "#7EE787",
    "accent3": "#FFA657",
    "gradient_start": "#0D1117",
    "gradient_end": "#58A6FF",
}

MONTH_NAMES_VI = [
    "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
    "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
    "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
]


# ==============================================================================
# LOAD DATA
# ==============================================================================
def load_data() -> dict:
    """Load tất cả dữ liệu có sẵn và trả về dict các DataFrame."""
    data = {}

    # Open-Meteo (bắt buộc)
    logger.info("Loading Open-Meteo data...")
    df_om = pd.read_csv(OPENMETEO_OUTPUT, parse_dates=["datetime"])
    df_om["datetime"] = pd.to_datetime(df_om["datetime"], utc=True).dt.tz_convert(TIMEZONE)
    data["openmeteo"] = df_om
    logger.info("  Open-Meteo: %d records", len(df_om))

    # ENSO
    if ENSO_OUTPUT.exists():
        logger.info("Loading ENSO data...")
        df_enso = pd.read_csv(ENSO_OUTPUT, parse_dates=["datetime"])
        df_enso["datetime"] = pd.to_datetime(df_enso["datetime"], utc=True).dt.tz_convert(TIMEZONE)
        data["enso"] = df_enso
        logger.info("  ENSO: %d records", len(df_enso))

    # ERA5 SST (nếu có)
    if ERA5_SST_OUTPUT.exists():
        logger.info("Loading ERA5 SST data...")
        df_sst = pd.read_csv(ERA5_SST_OUTPUT, parse_dates=["datetime"])
        df_sst["datetime"] = pd.to_datetime(df_sst["datetime"], utc=True).dt.tz_convert(TIMEZONE)
        data["sst"] = df_sst
        logger.info("  ERA5 SST: %d records", len(df_sst))

    # ERA5 Pressure Levels (nếu có)
    if ERA5_PRESSURE_OUTPUT.exists():
        logger.info("Loading ERA5 Pressure Levels data...")
        df_pl = pd.read_csv(ERA5_PRESSURE_OUTPUT, parse_dates=["datetime"])
        df_pl["datetime"] = pd.to_datetime(df_pl["datetime"], utc=True).dt.tz_convert(TIMEZONE)
        data["pressure"] = df_pl
        logger.info("  ERA5 PL: %d records", len(df_pl))

    return data


def merge_for_eda(data: dict) -> pd.DataFrame:
    """Merge tất cả nguồn dữ liệu thành 1 DataFrame cho EDA."""
    df = data["openmeteo"].copy()
    df["datetime"] = df["datetime"].dt.floor("h")

    if "enso" in data:
        df_enso = data["enso"].copy()
        df_enso["datetime"] = df_enso["datetime"].dt.floor("h")
        df = df.merge(df_enso, on="datetime", how="left")

    if "sst" in data:
        df_sst = data["sst"].copy()
        df_sst["datetime"] = df_sst["datetime"].dt.floor("h")
        df = df.merge(df_sst, on="datetime", how="left")

    if "pressure" in data:
        df_pl = data["pressure"].copy()
        df_pl["datetime"] = df_pl["datetime"].dt.floor("h")
        df = df.merge(df_pl, on="datetime", how="left")

    # Fill NaN cho cột ENSO bằng ffill (hợp lý vì ONI là monthly)
    if "oni_anom" in df.columns:
        df["oni_anom"] = df["oni_anom"].ffill().bfill()

    df = df.sort_values("datetime").reset_index(drop=True)

    # Thêm cột phụ trợ
    df["month"] = df["datetime"].dt.month
    df["hour"] = df["datetime"].dt.hour
    df["year"] = df["datetime"].dt.year
    df["day_of_year"] = df["datetime"].dt.dayofyear
    df["is_rainy"] = (df["precipitation"] > 0).astype(int)

    # Mùa khí hậu miền Trung
    df["season"] = df["month"].map(lambda m: "Mùa mưa" if m >= 9 or m <= 1 else "Mùa khô")

    logger.info("Merged DataFrame: %d records, %d columns", len(df), len(df.columns))
    return df


# ==============================================================================
# BIỂU ĐỒ 1: PHÂN BỐ LƯỢNG MƯA (TARGET DISTRIBUTION)
# ==============================================================================
def plot_01_target_distribution(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    Lượng mưa (target) có phân bố cực kỳ lệch phải (right-skewed).
    Biểu đồ này cho thấy:
      - Class imbalance: bao nhiêu % giờ không mưa vs có mưa
      - Heavy-tail: mưa cực đoan phân bố thế nào
      - Quyết định cần log-transform, cần sampling strategy, hay loss function đặc biệt
    """
    logger.info("Plotting 01: Target Distribution...")

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle("BIỂU ĐỒ 1: PHÂN BỐ LƯỢNG MƯA — BIẾN TARGET",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=0.98)

    gs = gridspec.GridSpec(2, 3, hspace=0.35, wspace=0.3,
                           left=0.06, right=0.96, top=0.90, bottom=0.08)

    rain = df["precipitation"]
    rain_pos = rain[rain > 0]

    # --- (a) Histogram toàn bộ ---
    ax1 = fig.add_subplot(gs[0, 0])
    bins = np.concatenate([
        np.array([0]),
        np.linspace(0.01, 1, 20),
        np.linspace(1, 5, 15),
        np.linspace(5, 20, 10),
        np.linspace(20, rain.max() + 1, 5),
    ])
    bins = np.unique(bins)
    ax1.hist(rain, bins=bins, color=COLORS["rain"], alpha=0.8, edgecolor="#0D1117", linewidth=0.3)
    ax1.set_yscale("log")
    ax1.set_xlabel("Lượng mưa (mm/h)")
    ax1.set_ylabel("Số lượng giờ (log scale)")
    ax1.set_title("(a) Histogram toàn bộ", fontweight="bold")
    ax1.grid(True, alpha=0.3)

    # --- (b) Pie chart: mưa vs không mưa ---
    ax2 = fig.add_subplot(gs[0, 1])
    no_rain = (rain == 0).sum()
    light = ((rain > 0) & (rain <= 2.5)).sum()
    moderate = ((rain > 2.5) & (rain <= 10)).sum()
    heavy = ((rain > 10) & (rain <= 30)).sum()
    extreme = (rain > 30).sum()

    sizes = [no_rain, light, moderate, heavy, extreme]
    labels = [
        f"Không mưa\n({no_rain/len(rain)*100:.1f}%)",
        f"Mưa nhẹ ≤2.5\n({light/len(rain)*100:.1f}%)",
        f"Mưa vừa 2.5-10\n({moderate/len(rain)*100:.2f}%)",
        f"Mưa lớn 10-30\n({heavy/len(rain)*100:.2f}%)",
        f"Mưa rất lớn >30\n({extreme/len(rain)*100:.3f}%)",
    ]
    colors_pie = ["#30363D", "#58A6FF", "#3FB950", "#FFA657", "#F85149"]
    explode = (0, 0.03, 0.05, 0.08, 0.12)

    wedges, texts = ax2.pie(
        sizes, labels=labels, colors=colors_pie, explode=explode,
        startangle=90, textprops={"fontsize": 8, "color": "#C9D1D9"},
    )
    ax2.set_title("(b) Phân loại cường độ mưa", fontweight="bold")

    # --- (c) Box plot theo mùa ---
    ax3 = fig.add_subplot(gs[0, 2])
    rain_wet = rain_pos[df.loc[rain_pos.index, "season"] == "Mùa mưa"]
    rain_dry = rain_pos[df.loc[rain_pos.index, "season"] == "Mùa khô"]

    bp = ax3.boxplot(
        [rain_wet.values, rain_dry.values],
        labels=["Mùa mưa\n(T9-T1)", "Mùa khô\n(T2-T8)"],
        patch_artist=True,
        boxprops=dict(facecolor=COLORS["rain"], alpha=0.4),
        medianprops=dict(color=COLORS["rain_heavy"], linewidth=2),
        flierprops=dict(marker="o", markerfacecolor=COLORS["rain_heavy"],
                        markersize=2, alpha=0.3),
        whiskerprops=dict(color="#8B949E"),
        capprops=dict(color="#8B949E"),
    )
    ax3.set_ylabel("Lượng mưa (mm/h)")
    ax3.set_title("(c) Phân bố theo mùa (chỉ giờ có mưa)", fontweight="bold")
    ax3.grid(True, alpha=0.3, axis="y")

    # --- (d) Histogram phần mưa > 0 (log-scale) ---
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.hist(np.log1p(rain_pos), bins=60, color=COLORS["accent1"], alpha=0.8,
             edgecolor="#0D1117", linewidth=0.3)
    ax4.set_xlabel("log(1 + precipitation)")
    ax4.set_ylabel("Số lượng giờ")
    ax4.set_title("(d) Log-transform (chỉ giờ có mưa)", fontweight="bold")
    ax4.grid(True, alpha=0.3)
    # Thêm thống kê
    ax4.text(0.95, 0.95,
             f"Skewness: {rain_pos.skew():.2f}\nKurtosis: {rain_pos.kurtosis():.2f}",
             transform=ax4.transAxes, ha="right", va="top",
             fontsize=9, color="#8B949E",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#0D1117", edgecolor="#30363D"))

    # --- (e) CDF ---
    ax5 = fig.add_subplot(gs[1, 1])
    sorted_rain = np.sort(rain_pos.values)
    cdf = np.arange(1, len(sorted_rain) + 1) / len(sorted_rain)
    ax5.plot(sorted_rain, cdf, color=COLORS["rain"], linewidth=1.5)
    ax5.fill_between(sorted_rain, cdf, alpha=0.15, color=COLORS["rain"])

    # Đánh dấu các ngưỡng quan trọng
    for threshold, label, color in [
        (2.5, "Nhẹ (2.5mm)", "#3FB950"),
        (10, "Vừa (10mm)", "#FFA657"),
        (30, "Lớn (30mm)", "#F85149"),
    ]:
        pct = (rain_pos <= threshold).mean()
        ax5.axvline(threshold, color=color, linestyle="--", alpha=0.7, linewidth=1)
        ax5.annotate(f"{label}\n{pct*100:.1f}%", xy=(threshold, pct),
                     fontsize=7.5, color=color, ha="left", va="bottom",
                     xytext=(5, 5), textcoords="offset points")

    ax5.set_xlabel("Lượng mưa (mm/h)")
    ax5.set_ylabel("CDF (xác suất tích lũy)")
    ax5.set_title("(e) CDF lượng mưa (giờ có mưa)", fontweight="bold")
    ax5.grid(True, alpha=0.3)

    # --- (f) Thống kê tóm tắt ---
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")

    stats_text = (
        f"THỐNG KÊ TỔNG HỢP\n"
        f"{'─' * 35}\n\n"
        f"Tổng số giờ:     {len(rain):>10,}\n"
        f"Giờ không mưa:   {no_rain:>10,}  ({no_rain/len(rain)*100:.1f}%)\n"
        f"Giờ có mưa:      {len(rain_pos):>10,}  ({len(rain_pos)/len(rain)*100:.1f}%)\n\n"
        f"{'─' * 35}\n"
        f"Lượng mưa trung bình:    {rain.mean():.3f} mm/h\n"
        f"Trung bình (có mưa):     {rain_pos.mean():.3f} mm/h\n"
        f"Trung vị (có mưa):       {rain_pos.median():.3f} mm/h\n"
        f"Tối đa:                  {rain.max():.1f} mm/h\n"
        f"P95 (có mưa):            {rain_pos.quantile(0.95):.2f} mm/h\n"
        f"P99 (có mưa):            {rain_pos.quantile(0.99):.2f} mm/h\n\n"
        f"{'─' * 35}\n"
        f"Skewness:     {rain.skew():.2f}\n"
        f"Kurtosis:     {rain.kurtosis():.2f}\n\n"
        f"→ Class imbalance ratio: 1:{no_rain//max(len(rain_pos),1)}\n"
        f"→ Cần log-transform hoặc\n"
        f"  weighted loss function"
    )

    ax6.text(0.05, 0.95, stats_text, transform=ax6.transAxes,
             fontsize=10, fontfamily="monospace", color="#C9D1D9",
             verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#0D1117",
                       edgecolor="#30363D", alpha=0.9))

    output_path = EDA_DIR / "01_target_distribution.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# BIỂU ĐỒ 2: MÙA VỤ LƯỢNG MƯA (MONTHLY SEASONALITY)
# ==============================================================================
def plot_02_monthly_seasonality(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    Đà Nẵng nằm ở miền Trung Việt Nam — mưa nhiều T9-T12 do gió mùa Đông Bắc
    gặp địa hình Trường Sơn. Biểu đồ cho thấy:
      - Chu kỳ mùa rõ rệt → model cần temporal encoding
      - Sự biến thiên giữa các năm → năm nào ENSO ảnh hưởng mạnh?
      - Biên độ mùa mưa/khô → preprocessing/normalization strategy
    """
    logger.info("Plotting 02: Monthly Seasonality...")

    fig = plt.figure(figsize=(18, 12))
    fig.suptitle("BIỂU ĐỒ 2: TÍNH MÙA VỤ LƯỢNG MƯA ĐÀ NẴNG",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=0.98)

    gs = gridspec.GridSpec(2, 2, hspace=0.32, wspace=0.25,
                           left=0.07, right=0.95, top=0.90, bottom=0.08)

    # --- (a) Tổng lượng mưa theo tháng (mean + std) ---
    ax1 = fig.add_subplot(gs[0, 0])

    monthly_stats = df.groupby("month")["precipitation"].agg(["mean", "std", "sum"])
    months = range(1, 13)

    ax1.bar(months, monthly_stats["mean"], color=COLORS["rain"], alpha=0.7,
            edgecolor="#0D1117", linewidth=0.5, label="Trung bình")
    ax1.errorbar(months, monthly_stats["mean"], yerr=monthly_stats["std"],
                 fmt="none", ecolor=COLORS["rain_heavy"], elinewidth=1.5,
                 capsize=3, capthick=1, label="±1 Std")

    ax1.set_xticks(months)
    ax1.set_xticklabels(MONTH_NAMES_VI, rotation=45, ha="right", fontsize=8)
    ax1.set_ylabel("Lượng mưa trung bình (mm/h)")
    ax1.set_title("(a) Lượng mưa trung bình theo tháng", fontweight="bold")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3, axis="y")

    # Highlight mùa mưa
    ax1.axvspan(8.5, 12.5, alpha=0.08, color=COLORS["rain"], label="Mùa mưa")
    ax1.text(10.5, ax1.get_ylim()[1] * 0.92, "MÙA MƯA", ha="center",
             fontsize=9, color=COLORS["rain"], fontweight="bold", alpha=0.7)

    # --- (b) Heatmap tháng × năm ---
    ax2 = fig.add_subplot(gs[0, 1])

    pivot = df.groupby(["year", "month"])["precipitation"].sum().unstack(fill_value=0)
    years = sorted(df["year"].unique())

    cmap = LinearSegmentedColormap.from_list("rain_cmap",
        ["#0D1117", "#1a3a5c", "#58A6FF", "#FFA657", "#F85149"])

    im = ax2.imshow(pivot.values, aspect="auto", cmap=cmap, interpolation="nearest")
    ax2.set_xticks(range(12))
    ax2.set_xticklabels([f"T{m}" for m in range(1, 13)], fontsize=8)
    ax2.set_yticks(range(len(years)))
    ax2.set_yticklabels(years, fontsize=8)
    ax2.set_title("(b) Heatmap tổng mưa: Tháng × Năm (mm)", fontweight="bold")

    cbar = plt.colorbar(im, ax=ax2, shrink=0.8, pad=0.02)
    cbar.set_label("Tổng mưa (mm)", fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    # --- (c) Tần suất mưa theo tháng ---
    ax3 = fig.add_subplot(gs[1, 0])

    rain_freq = df.groupby("month")["is_rainy"].mean() * 100
    colors_bar = [COLORS["rain"] if m >= 9 or m <= 1 else COLORS["accent1"]
                  for m in range(1, 13)]

    bars = ax3.bar(months, rain_freq.values, color=colors_bar, alpha=0.8,
                   edgecolor="#0D1117", linewidth=0.5)
    ax3.set_xticks(months)
    ax3.set_xticklabels(MONTH_NAMES_VI, rotation=45, ha="right", fontsize=8)
    ax3.set_ylabel("Tần suất mưa (%)")
    ax3.set_title("(c) Tần suất giờ có mưa theo tháng", fontweight="bold")
    ax3.grid(True, alpha=0.3, axis="y")

    # Annotate values
    for bar, val in zip(bars, rain_freq.values):
        ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.3,
                 f"{val:.1f}%", ha="center", va="bottom", fontsize=7, color="#8B949E")

    # --- (d) Violin plot theo tháng (chỉ giờ có mưa) ---
    ax4 = fig.add_subplot(gs[1, 1])

    rain_by_month = [df[(df["month"] == m) & (df["precipitation"] > 0)]["precipitation"].values
                     for m in range(1, 13)]
    # Filter empty arrays
    valid_months = [(i+1, data) for i, data in enumerate(rain_by_month) if len(data) > 0]

    if valid_months:
        positions = [m for m, _ in valid_months]
        data_arrays = [d for _, d in valid_months]

        vp = ax4.violinplot(data_arrays, positions=positions, showmeans=True,
                            showmedians=True, showextrema=False)
        for body in vp["bodies"]:
            body.set_facecolor(COLORS["rain"])
            body.set_alpha(0.4)
            body.set_edgecolor(COLORS["rain"])
        if "cmeans" in vp:
            vp["cmeans"].set_color(COLORS["rain_heavy"])
        if "cmedians" in vp:
            vp["cmedians"].set_color(COLORS["accent2"])

    ax4.set_xticks(months)
    ax4.set_xticklabels(MONTH_NAMES_VI, rotation=45, ha="right", fontsize=8)
    ax4.set_ylabel("Lượng mưa (mm/h)")
    ax4.set_title("(d) Violin plot lượng mưa theo tháng (giờ có mưa)", fontweight="bold")
    ax4.grid(True, alpha=0.3, axis="y")
    ax4.set_ylim(0, min(df[df["precipitation"] > 0]["precipitation"].quantile(0.99) * 1.2, 50))

    output_path = EDA_DIR / "02_monthly_seasonality.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# BIỂU ĐỒ 3: CORRELATION HEATMAP
# ==============================================================================
def plot_03_correlation_heatmap(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    Trực tiếp trả lời: "Feature nào tương quan với mưa?"
      - Pearson correlation: mối quan hệ tuyến tính
      - Spearman correlation: mối quan hệ đơn điệu (robust hơn cho dữ liệu skewed)
      - Phát hiện multicollinearity giữa features
    """
    logger.info("Plotting 03: Correlation Heatmap...")

    # Lấy cột số (loại bỏ datetime và cột phụ trợ)
    exclude_cols = {"datetime", "month", "hour", "year", "day_of_year", "is_rainy", "season"}
    numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c not in exclude_cols]

    if len(numeric_cols) < 2:
        logger.warning("  Không đủ cột số để tạo heatmap!")
        return

    df_num = df[numeric_cols].dropna()

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    fig.suptitle("BIỂU ĐỒ 3: MA TRẬN TƯƠNG QUAN GIỮA CÁC BIẾN",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=1.0)

    cmap = LinearSegmentedColormap.from_list("corr_cmap",
        ["#F85149", "#21262D", "#3FB950"])

    for ax, method, title in [
        (axes[0], "pearson", "(a) Pearson (tuyến tính)"),
        (axes[1], "spearman", "(b) Spearman (đơn điệu)"),
    ]:
        corr = df_num.corr(method=method)

        # Rename columns for readability
        rename_map = {
            "temperature_2m": "Temp 2m",
            "relative_humidity_2m": "RH 2m",
            "surface_pressure": "Pressure",
            "wind_speed_10m": "Wind Spd",
            "wind_direction_10m": "Wind Dir",
            "precipitation": "RAIN ★",
            "sea_surface_temperature": "SST",
            "u_wind_850hpa": "U-Wind 850",
            "v_wind_850hpa": "V-Wind 850",
            "specific_humidity_850hpa": "Sp.Hum 850",
            "oni_anom": "ONI/ENSO",
        }
        corr_display = corr.rename(index=rename_map, columns=rename_map)

        im = ax.imshow(corr_display.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")

        n = len(corr_display)
        ax.set_xticks(range(n))
        ax.set_xticklabels(corr_display.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(n))
        ax.set_yticklabels(corr_display.index, fontsize=8)

        # Annotate values
        for i in range(n):
            for j in range(n):
                val = corr_display.values[i, j]
                color = "#C9D1D9" if abs(val) < 0.5 else "#0D1117"
                weight = "bold" if abs(val) > 0.3 and i != j else "normal"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=7, color=color, fontweight=weight)

        ax.set_title(title, fontweight="bold", pad=12)

    plt.colorbar(im, ax=axes, shrink=0.6, pad=0.02, label="Hệ số tương quan")

    plt.tight_layout()
    output_path = EDA_DIR / "03_correlation_heatmap.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# BIỂU ĐỒ 4: MULTI-VARIABLE TIME SERIES
# ==============================================================================
def plot_04_timeseries(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    Cho thấy mối quan hệ temporal giữa các biến — đây chính là input
    mà Bi-LSTM/Informer sẽ học. Biểu đồ cho thấy:
      - Khi nào SST tăng → mưa tăng theo?
      - Humidity và mưa có đồng biến?
      - Trend dài hạn và biến đổi khí hậu
    """
    logger.info("Plotting 04: Multi-variable Time Series...")

    # Chọn 1 năm điển hình để hiển thị chi tiết (2020)
    sample_year = 2020
    df_year = df[df["year"] == sample_year].copy()

    if len(df_year) == 0:
        sample_year = df["year"].mode().iloc[0]
        df_year = df[df["year"] == sample_year].copy()

    # Resample daily mean cho dễ nhìn
    df_daily = df_year.set_index("datetime").resample("D").agg({
        "precipitation": "sum",
        "temperature_2m": "mean",
        "relative_humidity_2m": "mean",
        "surface_pressure": "mean",
        "wind_speed_10m": "mean",
    })
    if "oni_anom" in df_year.columns:
        df_daily["oni_anom"] = df_year.set_index("datetime")["oni_anom"].resample("D").mean()

    variables = [
        ("precipitation", "Lượng mưa (mm/ngày)", COLORS["rain"], True),
        ("temperature_2m", "Nhiệt độ 2m (°C)", COLORS["temperature"], False),
        ("relative_humidity_2m", "Độ ẩm tương đối (%)", COLORS["humidity"], False),
        ("surface_pressure", "Áp suất (hPa)", COLORS["pressure"], False),
        ("wind_speed_10m", "Tốc độ gió (km/h)", COLORS["wind"], False),
    ]
    if "oni_anom" in df_daily.columns:
        variables.append(("oni_anom", "ONI/ENSO Index", COLORS["sst"], False))

    n_vars = len(variables)
    fig, axes = plt.subplots(n_vars, 1, figsize=(18, 3 * n_vars + 2), sharex=True)
    fig.suptitle(f"BIỂU ĐỒ 4: CHUỖI THỜI GIAN ĐA BIẾN — NĂM {sample_year}",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=0.99)

    for i, (col, label, color, is_bar) in enumerate(variables):
        ax = axes[i]
        if col in df_daily.columns:
            if is_bar:
                ax.bar(df_daily.index, df_daily[col], color=color, alpha=0.7, width=0.8)
            else:
                ax.plot(df_daily.index, df_daily[col], color=color, linewidth=0.8, alpha=0.9)
                ax.fill_between(df_daily.index, df_daily[col], alpha=0.1, color=color)

            # Đánh dấu mùa mưa
            for m_start, m_end in [(9, 12)]:
                start = pd.Timestamp(f"{sample_year}-{m_start:02d}-01", tz=TIMEZONE)
                end = pd.Timestamp(f"{sample_year}-{m_end:02d}-31", tz=TIMEZONE)
                ax.axvspan(start, end, alpha=0.05, color=COLORS["rain"])

        ax.set_ylabel(label, fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

        # ONI: thêm zero line và color bands
        if col == "oni_anom":
            ax.axhline(0, color="#8B949E", linestyle="-", linewidth=0.5)
            ax.axhline(0.5, color=COLORS["enso_el"], linestyle="--", linewidth=0.5, alpha=0.5)
            ax.axhline(-0.5, color=COLORS["enso_la"], linestyle="--", linewidth=0.5, alpha=0.5)
            ax.fill_between(df_daily.index, 0, df_daily[col],
                            where=df_daily[col] >= 0.5,
                            alpha=0.2, color=COLORS["enso_el"], label="El Niño")
            ax.fill_between(df_daily.index, 0, df_daily[col],
                            where=df_daily[col] <= -0.5,
                            alpha=0.2, color=COLORS["enso_la"], label="La Niña")
            ax.legend(loc="upper right", fontsize=7)

    axes[-1].tick_params(axis="x", rotation=30, labelsize=8)
    plt.tight_layout()

    output_path = EDA_DIR / "04_timeseries_multivar.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# BIỂU ĐỒ 5: ẢNH HƯỞNG ENSO LÊN LƯỢNG MƯA
# ==============================================================================
def plot_05_enso_impact(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    ENSO là đặc trưng vĩ mô unique cho Việt Nam.
      - El Niño → khô hạn miền Trung
      - La Niña → mưa lớn, lũ lụt miền Trung
    Biểu đồ validate giả thuyết này bằng dữ liệu thực tế.
    """
    logger.info("Plotting 05: ENSO Impact...")

    if "oni_anom" not in df.columns:
        logger.warning("  Không có dữ liệu ENSO — bỏ qua biểu đồ 5")
        return

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle("BIỂU ĐỒ 5: ẢNH HƯỞNG ENSO (EL NIÑO / LA NIÑA) LÊN LƯỢNG MƯA ĐÀ NẴNG",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=0.98)

    gs = gridspec.GridSpec(2, 2, hspace=0.35, wspace=0.3,
                           left=0.07, right=0.95, top=0.90, bottom=0.08)

    # Phân loại ENSO phase
    df_copy = df.copy()
    df_copy["enso_phase"] = pd.cut(
        df_copy["oni_anom"],
        bins=[-np.inf, -0.5, 0.5, np.inf],
        labels=["La Niña", "Neutral", "El Niño"]
    )

    # --- (a) Scatter: ONI vs lượng mưa monthly ---
    ax1 = fig.add_subplot(gs[0, 0])
    monthly = df_copy.groupby([df_copy["datetime"].dt.to_period("M")]).agg({
        "precipitation": "sum",
        "oni_anom": "mean",
    }).reset_index()
    monthly["datetime"] = monthly["datetime"].dt.to_timestamp()

    colors_scatter = [COLORS["enso_el"] if x >= 0.5 else
                      COLORS["enso_la"] if x <= -0.5 else
                      COLORS["enso_neutral"]
                      for x in monthly["oni_anom"]]

    ax1.scatter(monthly["oni_anom"], monthly["precipitation"], c=colors_scatter,
                alpha=0.6, s=30, edgecolors="#0D1117", linewidth=0.3)

    # Regression line
    z = np.polyfit(monthly["oni_anom"], monthly["precipitation"], 1)
    p = np.poly1d(z)
    x_line = np.linspace(monthly["oni_anom"].min(), monthly["oni_anom"].max(), 100)
    ax1.plot(x_line, p(x_line), "--", color="#FFA657", linewidth=1.5, alpha=0.8)

    r_corr, p_val = stats.pearsonr(monthly["oni_anom"], monthly["precipitation"])
    ax1.text(0.05, 0.95, f"r = {r_corr:.3f}\np = {p_val:.4f}",
             transform=ax1.transAxes, fontsize=9, va="top",
             bbox=dict(boxstyle="round", facecolor="#0D1117", edgecolor="#30363D"))

    ax1.set_xlabel("ONI Index")
    ax1.set_ylabel("Tổng mưa tháng (mm)")
    ax1.set_title("(a) ONI vs Lượng mưa tháng", fontweight="bold")
    ax1.grid(True, alpha=0.3)

    # --- (b) Bar chart: Lượng mưa trung bình theo ENSO phase ---
    ax2 = fig.add_subplot(gs[0, 1])

    phase_stats = df_copy.groupby("enso_phase")["precipitation"].agg(["mean", "std", "count"])
    phase_stats = phase_stats.reindex(["La Niña", "Neutral", "El Niño"])
    phase_colors = [COLORS["enso_la"], COLORS["enso_neutral"], COLORS["enso_el"]]

    bars = ax2.bar(range(3), phase_stats["mean"], color=phase_colors, alpha=0.8,
                   edgecolor="#0D1117", linewidth=0.5)
    ax2.errorbar(range(3), phase_stats["mean"], yerr=phase_stats["std"],
                 fmt="none", ecolor="#C9D1D9", elinewidth=1, capsize=4)

    ax2.set_xticks(range(3))
    ax2.set_xticklabels(["La Niña\n(ONI ≤ -0.5)", "Neutral\n(-0.5 < ONI < 0.5)",
                          "El Niño\n(ONI ≥ 0.5)"], fontsize=9)
    ax2.set_ylabel("Lượng mưa trung bình (mm/h)")
    ax2.set_title("(b) Lượng mưa theo ENSO Phase", fontweight="bold")
    ax2.grid(True, alpha=0.3, axis="y")

    for bar, val in zip(bars, phase_stats["mean"]):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.005,
                 f"{val:.4f}", ha="center", va="bottom", fontsize=9, color="#C9D1D9")

    # --- (c) Monthly rainfall by ENSO phase ---
    ax3 = fig.add_subplot(gs[1, 0])

    for phase, color, ls in [("La Niña", COLORS["enso_la"], "-"),
                              ("Neutral", COLORS["enso_neutral"], "--"),
                              ("El Niño", COLORS["enso_el"], "-")]:
        phase_data = df_copy[df_copy["enso_phase"] == phase]
        monthly_phase = phase_data.groupby("month")["precipitation"].mean()
        ax3.plot(range(1, 13), monthly_phase.reindex(range(1, 13)).values,
                 color=color, linewidth=2, linestyle=ls, marker="o", markersize=4,
                 label=phase, alpha=0.9)

    ax3.set_xticks(range(1, 13))
    ax3.set_xticklabels(MONTH_NAMES_VI, rotation=45, ha="right", fontsize=8)
    ax3.set_ylabel("Lượng mưa trung bình (mm/h)")
    ax3.set_title("(c) Mùa vụ mưa theo ENSO Phase", fontweight="bold")
    ax3.legend(loc="upper left", fontsize=9)
    ax3.grid(True, alpha=0.3)

    # --- (d) ONI timeline + rainfall overlay ---
    ax4 = fig.add_subplot(gs[1, 1])

    monthly_oni = df_copy.groupby(df_copy["datetime"].dt.to_period("M")).agg({
        "oni_anom": "mean",
        "precipitation": "sum",
    }).reset_index()
    monthly_oni["datetime"] = monthly_oni["datetime"].dt.to_timestamp()

    ax4_twin = ax4.twinx()

    # ONI line
    ax4.fill_between(monthly_oni["datetime"], 0, monthly_oni["oni_anom"],
                     where=monthly_oni["oni_anom"] >= 0.5,
                     alpha=0.3, color=COLORS["enso_el"], label="El Niño")
    ax4.fill_between(monthly_oni["datetime"], 0, monthly_oni["oni_anom"],
                     where=monthly_oni["oni_anom"] <= -0.5,
                     alpha=0.3, color=COLORS["enso_la"], label="La Niña")
    ax4.plot(monthly_oni["datetime"], monthly_oni["oni_anom"],
             color="#C9D1D9", linewidth=1, alpha=0.8)
    ax4.axhline(0, color="#8B949E", linestyle="-", linewidth=0.3)

    # Rainfall bars
    ax4_twin.bar(monthly_oni["datetime"], monthly_oni["precipitation"],
                 width=25, alpha=0.4, color=COLORS["rain"], label="Lượng mưa")

    ax4.set_ylabel("ONI Index", color="#C9D1D9")
    ax4_twin.set_ylabel("Tổng mưa tháng (mm)", color=COLORS["rain"])
    ax4.set_title("(d) Timeline ONI + Lượng mưa", fontweight="bold")
    ax4.legend(loc="upper left", fontsize=8)
    ax4_twin.legend(loc="upper right", fontsize=8)
    ax4.grid(True, alpha=0.3)
    ax4.tick_params(axis="x", rotation=30, labelsize=8)

    output_path = EDA_DIR / "05_enso_impact.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# BIỂU ĐỒ 6: DIURNAL PATTERN (CHU KỲ TRONG NGÀY)
# ==============================================================================
def plot_06_diurnal_pattern(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    Mưa cục bộ có chu kỳ ngày rõ rệt (mưa đối lưu chiều/tối).
    Biểu đồ cho thấy:
      - Giờ nào mưa nhiều nhất → model cần hour encoding
      - Pattern khác nhau mùa mưa vs mùa khô → interaction feature
      - Phối hợp với nhiệt độ/humidity → hiểu cơ chế đối lưu
    """
    logger.info("Plotting 06: Diurnal Pattern...")

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle("BIỂU ĐỒ 6: CHU KỲ TRONG NGÀY (DIURNAL PATTERN) — GIỜ VN (UTC+7)",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=0.98)

    gs = gridspec.GridSpec(2, 2, hspace=0.35, wspace=0.3,
                           left=0.07, right=0.95, top=0.90, bottom=0.08)

    hours = range(24)

    # --- (a) Lượng mưa trung bình theo giờ ---
    ax1 = fig.add_subplot(gs[0, 0])

    hourly_rain = df.groupby("hour")["precipitation"].mean()
    ax1.bar(hours, hourly_rain.values, color=COLORS["rain"], alpha=0.8,
            edgecolor="#0D1117", linewidth=0.5)
    ax1.set_xlabel("Giờ trong ngày (UTC+7)")
    ax1.set_ylabel("Lượng mưa TB (mm/h)")
    ax1.set_title("(a) Lượng mưa trung bình theo giờ", fontweight="bold")
    ax1.set_xticks(hours)
    ax1.set_xticklabels([f"{h:02d}" for h in hours], fontsize=7)
    ax1.grid(True, alpha=0.3, axis="y")

    # Highlight peak
    peak_hour = hourly_rain.idxmax()
    ax1.annotate(f"Peak: {peak_hour:02d}h\n{hourly_rain.max():.3f} mm/h",
                 xy=(peak_hour, hourly_rain.max()),
                 xytext=(peak_hour + 3, hourly_rain.max() * 1.1),
                 arrowprops=dict(arrowstyle="->", color=COLORS["rain_heavy"]),
                 fontsize=9, color=COLORS["rain_heavy"], fontweight="bold")

    # --- (b) Diurnal pattern by season ---
    ax2 = fig.add_subplot(gs[0, 1])

    for season, color, ls in [("Mùa mưa", COLORS["rain"], "-"),
                                ("Mùa khô", COLORS["accent1"], "--")]:
        hourly_season = df[df["season"] == season].groupby("hour")["precipitation"].mean()
        ax2.plot(hours, hourly_season.reindex(hours).values,
                 color=color, linewidth=2, linestyle=ls, marker="o",
                 markersize=4, label=season)
        ax2.fill_between(hours, hourly_season.reindex(hours).values,
                         alpha=0.1, color=color)

    ax2.set_xlabel("Giờ trong ngày (UTC+7)")
    ax2.set_ylabel("Lượng mưa TB (mm/h)")
    ax2.set_title("(b) Diurnal pattern: Mùa mưa vs Mùa khô", fontweight="bold")
    ax2.set_xticks(hours)
    ax2.set_xticklabels([f"{h:02d}" for h in hours], fontsize=7)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    # --- (c) Heatmap: Giờ × Tháng ---
    ax3 = fig.add_subplot(gs[1, 0])

    pivot_hm = df.groupby(["hour", "month"])["precipitation"].mean().unstack(fill_value=0)

    cmap_diurnal = LinearSegmentedColormap.from_list("diurnal",
        ["#0D1117", "#1a3a5c", "#58A6FF", "#FFA657", "#F85149"])

    im = ax3.imshow(pivot_hm.values, aspect="auto", cmap=cmap_diurnal, interpolation="bilinear")
    ax3.set_yticks(range(24))
    ax3.set_yticklabels([f"{h:02d}:00" for h in range(24)], fontsize=7)
    ax3.set_xticks(range(12))
    ax3.set_xticklabels([f"T{m}" for m in range(1, 13)], fontsize=8)
    ax3.set_xlabel("Tháng")
    ax3.set_ylabel("Giờ (UTC+7)")
    ax3.set_title("(c) Heatmap: Giờ × Tháng", fontweight="bold")
    plt.colorbar(im, ax=ax3, shrink=0.8, label="TB mưa (mm/h)")

    # --- (d) Multi-variable diurnal cycle ---
    ax4 = fig.add_subplot(gs[1, 1])

    vars_diurnal = [
        ("temperature_2m", "Temp 2m", COLORS["temperature"]),
        ("relative_humidity_2m", "RH 2m", COLORS["humidity"]),
    ]

    ax4_twin = ax4.twinx()

    for var, label, color in vars_diurnal:
        hourly_var = df.groupby("hour")[var].mean()
        norm_var = (hourly_var - hourly_var.min()) / (hourly_var.max() - hourly_var.min())
        ax4.plot(hours, norm_var.values, color=color, linewidth=2, label=label)

    # Rainfall normalized
    hourly_rain_norm = (hourly_rain - hourly_rain.min()) / (hourly_rain.max() - hourly_rain.min())
    ax4_twin.bar(hours, hourly_rain_norm.values, color=COLORS["rain"], alpha=0.3,
                 label="Rain", edgecolor="none")

    ax4.set_xlabel("Giờ (UTC+7)")
    ax4.set_ylabel("Giá trị chuẩn hóa [0, 1]")
    ax4.set_title("(d) So sánh chu kỳ ngày: Temp, RH vs Rain", fontweight="bold")
    ax4.set_xticks(hours)
    ax4.set_xticklabels([f"{h:02d}" for h in hours], fontsize=7)
    ax4.legend(loc="upper left", fontsize=8)
    ax4_twin.legend(loc="upper right", fontsize=8)
    ax4.grid(True, alpha=0.3)
    ax4_twin.set_ylabel("Rain (norm)", color=COLORS["rain"])

    output_path = EDA_DIR / "06_diurnal_pattern.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# BIỂU ĐỒ 7: LAG CORRELATION ANALYSIS
# ==============================================================================
def plot_07_lag_correlation(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    Bi-LSTM/Informer dự đoán dựa trên cửa sổ thời gian quá khứ.
    Biểu đồ này cho thấy:
      - Feature X ở t-lag có tương quan với mưa ở t không?
      - Lead time: bao nhiêu giờ trước feature bắt đầu "dự báo" mưa?
      - Giúp chọn window size tối ưu cho model
      - ERA5 features có lead time dài hơn? → quan trọng cho dự đoán dài hạn
    """
    logger.info("Plotting 07: Lag Correlation Analysis...")

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle("BIỂU ĐỒ 7: PHÂN TÍCH TƯƠNG QUAN TRỄ (LAG CORRELATION)",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=0.98)

    gs = gridspec.GridSpec(2, 2, hspace=0.35, wspace=0.3,
                           left=0.07, right=0.95, top=0.90, bottom=0.08)

    max_lag = 72  # 3 ngày
    lags = range(0, max_lag + 1)

    features_to_check = [
        ("temperature_2m", "Nhiệt độ 2m", COLORS["temperature"]),
        ("relative_humidity_2m", "Độ ẩm RH 2m", COLORS["humidity"]),
        ("surface_pressure", "Áp suất", COLORS["pressure"]),
        ("wind_speed_10m", "Tốc độ gió", COLORS["wind"]),
    ]

    # Thêm ERA5 nếu có
    era5_features = []
    if "sea_surface_temperature" in df.columns:
        era5_features.append(("sea_surface_temperature", "SST", COLORS["sst"]))
    if "specific_humidity_850hpa" in df.columns:
        era5_features.append(("specific_humidity_850hpa", "Sp.Hum 850hPa", COLORS["accent2"]))
    if "oni_anom" in df.columns:
        features_to_check.append(("oni_anom", "ONI/ENSO", COLORS["accent3"]))

    # Lấy sample để tính nhanh hơn
    rain = df["precipitation"].values

    # --- (a) Lag correlation: biến bề mặt ---
    ax1 = fig.add_subplot(gs[0, 0])

    for col, label, color in features_to_check:
        if col not in df.columns:
            continue
        feature = df[col].values
        lag_corrs = []
        for lag in lags:
            if lag == 0:
                corr = np.corrcoef(feature, rain)[0, 1]
            else:
                corr = np.corrcoef(feature[:-lag], rain[lag:])[0, 1]
            lag_corrs.append(corr)
        ax1.plot(lags, lag_corrs, color=color, linewidth=1.5, label=label, alpha=0.85)

    ax1.axhline(0, color="#8B949E", linestyle="-", linewidth=0.3)
    ax1.set_xlabel("Lag (giờ)")
    ax1.set_ylabel("Pearson Correlation")
    ax1.set_title("(a) Lag Correlation: Biến bề mặt → Mưa", fontweight="bold")
    ax1.legend(fontsize=8, loc="best")
    ax1.grid(True, alpha=0.3)

    # --- (b) Lag correlation: biến ERA5 (nếu có) ---
    ax2 = fig.add_subplot(gs[0, 1])

    if era5_features:
        for col, label, color in era5_features:
            feature = df[col].dropna().values
            rain_aligned = df.loc[df[col].notna(), "precipitation"].values
            lag_corrs = []
            max_lag_era5 = min(72, len(feature) - 1)
            lags_era5 = range(0, max_lag_era5 + 1)
            for lag in lags_era5:
                if lag == 0:
                    corr = np.corrcoef(feature, rain_aligned)[0, 1]
                else:
                    corr = np.corrcoef(feature[:-lag], rain_aligned[lag:])[0, 1]
                lag_corrs.append(corr)
            ax2.plot(lags_era5, lag_corrs, color=color, linewidth=1.5, label=label, alpha=0.85)

        ax2.set_title("(b) Lag Correlation: ERA5 → Mưa", fontweight="bold")
    else:
        ax2.text(0.5, 0.5, "ERA5 chưa có dữ liệu\n\nSẽ bổ sung khi\nERA5 download hoàn tất",
                 ha="center", va="center", fontsize=12, color="#8B949E",
                 transform=ax2.transAxes)
        ax2.set_title("(b) Lag Correlation: ERA5 → Mưa [PENDING]", fontweight="bold")

    ax2.axhline(0, color="#8B949E", linestyle="-", linewidth=0.3)
    ax2.set_xlabel("Lag (giờ)")
    ax2.set_ylabel("Pearson Correlation")
    ax2.legend(fontsize=8, loc="best")
    ax2.grid(True, alpha=0.3)

    # --- (c) Auto-correlation của mưa ---
    ax3 = fig.add_subplot(gs[1, 0])

    max_lag_auto = 168  # 7 ngày
    autocorrs = []
    for lag in range(0, max_lag_auto + 1):
        if lag == 0:
            autocorrs.append(1.0)
        else:
            corr = np.corrcoef(rain[:-lag], rain[lag:])[0, 1]
            autocorrs.append(corr)

    ax3.plot(range(max_lag_auto + 1), autocorrs, color=COLORS["rain"], linewidth=1.5)
    ax3.fill_between(range(max_lag_auto + 1), autocorrs, alpha=0.15, color=COLORS["rain"])

    # Confidence interval
    n = len(rain)
    ci = 1.96 / np.sqrt(n)
    ax3.axhspan(-ci, ci, alpha=0.1, color="#8B949E", label="95% CI")

    # Mark key lags
    for lag_mark in [24, 48, 72, 168]:
        if lag_mark <= max_lag_auto:
            ax3.axvline(lag_mark, color="#30363D", linestyle=":", linewidth=0.5)
            ax3.text(lag_mark, ax3.get_ylim()[1] * 0.95, f"{lag_mark}h\n({lag_mark//24}d)",
                     ha="center", fontsize=7, color="#8B949E")

    ax3.axhline(0, color="#8B949E", linestyle="-", linewidth=0.3)
    ax3.set_xlabel("Lag (giờ)")
    ax3.set_ylabel("Auto-correlation")
    ax3.set_title("(c) Auto-correlation lượng mưa (7 ngày)", fontweight="bold")
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=8)

    # --- (d) Summary table ---
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")

    summary_lines = ["TỔNG KẾT LAG CORRELATION", "─" * 45, ""]
    summary_lines.append(f"{'Feature':<22} {'Peak Corr':>10} {'Peak Lag':>10}")
    summary_lines.append("─" * 45)

    all_features = features_to_check + era5_features
    for col, label, _ in all_features:
        if col not in df.columns:
            continue
        feature = df[col].dropna().values
        rain_aligned = df.loc[df[col].notna(), "precipitation"].values
        best_corr = 0
        best_lag = 0
        for lag in range(0, min(73, len(feature))):
            if lag == 0:
                corr = np.corrcoef(feature, rain_aligned)[0, 1]
            else:
                corr = np.corrcoef(feature[:-lag], rain_aligned[lag:])[0, 1]
            if abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

        summary_lines.append(f"{label:<22} {best_corr:>+10.4f} {best_lag:>7d} h")

    summary_lines.append("")
    summary_lines.append("─" * 45)
    summary_lines.append("")
    summary_lines.append("→ Peak Lag cho biết bao nhiêu giờ")
    summary_lines.append("  TRƯỚC feature tương quan mạnh nhất")
    summary_lines.append("  với mưa. Giúp chọn window size")
    summary_lines.append("  cho Bi-LSTM / Informer.")

    ax4.text(0.05, 0.95, "\n".join(summary_lines),
             transform=ax4.transAxes, fontsize=9.5, fontfamily="monospace",
             color="#C9D1D9", verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#0D1117",
                       edgecolor="#30363D", alpha=0.9))

    output_path = EDA_DIR / "07_lag_correlation.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# BIỂU ĐỒ 8: FEATURE IMPORTANCE (MUTUAL INFORMATION)
# ==============================================================================
def plot_08_feature_importance(df: pd.DataFrame):
    """
    VÌ SAO QUAN TRỌNG:
    Mutual Information (MI) đo lường mối quan hệ phi tuyến giữa feature và target,
    mạnh hơn Pearson correlation. Trực tiếp trả lời:
      - Feature nào đóng góp nhiều nhất cho dự đoán mưa?
      - Nhóm biến nào (bề mặt vs ERA5 vs ENSO) có giá trị nhất?
      - Có đáng triển khai ERA5 cho toàn bộ 63 tỉnh thành không?
    """
    logger.info("Plotting 08: Feature Importance (Mutual Information)...")

    exclude_cols = {"datetime", "month", "hour", "year", "day_of_year", "is_rainy",
                    "season", "precipitation"}
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c not in exclude_cols]

    if len(feature_cols) < 2:
        logger.warning("  Không đủ features — bỏ qua biểu đồ 8")
        return

    # Lấy sample để tính nhanh (MI tốn tài nguyên)
    sample_size = min(50000, len(df))
    df_sample = df.sample(n=sample_size, random_state=42)

    X = df_sample[feature_cols].fillna(0).values
    y = df_sample["precipitation"].values

    # Tính MI
    logger.info("  Đang tính Mutual Information (n=%d)...", sample_size)
    mi_scores = mutual_info_regression(X, y, random_state=42, n_neighbors=5)

    # Phân nhóm features
    feature_groups = {}
    group_labels = {}
    for i, col in enumerate(feature_cols):
        if col in ["temperature_2m", "relative_humidity_2m", "surface_pressure",
                    "wind_speed_10m", "wind_direction_10m"]:
            feature_groups[col] = "Bề mặt (Open-Meteo)"
        elif col in ["sea_surface_temperature", "u_wind_850hpa", "v_wind_850hpa",
                      "specific_humidity_850hpa"]:
            feature_groups[col] = "ERA5 Reanalysis"
        elif col == "oni_anom":
            feature_groups[col] = "ENSO (NOAA)"
        else:
            feature_groups[col] = "Khác"

    # Sort by MI score
    mi_df = pd.DataFrame({
        "feature": feature_cols,
        "mi_score": mi_scores,
        "group": [feature_groups.get(c, "Khác") for c in feature_cols],
    }).sort_values("mi_score", ascending=True)

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle("BIỂU ĐỒ 8: FEATURE IMPORTANCE — MUTUAL INFORMATION",
                 fontsize=18, fontweight="bold", color="#58A6FF", y=0.98)

    gs = gridspec.GridSpec(1, 2, wspace=0.35,
                           left=0.10, right=0.95, top=0.90, bottom=0.08,
                           width_ratios=[1.5, 1])

    # --- (a) MI bar chart ---
    ax1 = fig.add_subplot(gs[0, 0])

    group_colors = {
        "Bề mặt (Open-Meteo)": COLORS["rain"],
        "ERA5 Reanalysis": COLORS["sst"],
        "ENSO (NOAA)": COLORS["accent3"],
        "Khác": "#8B949E",
    }

    rename_display = {
        "temperature_2m": "Nhiệt độ 2m",
        "relative_humidity_2m": "Độ ẩm RH 2m",
        "surface_pressure": "Áp suất bề mặt",
        "wind_speed_10m": "Tốc độ gió 10m",
        "wind_direction_10m": "Hướng gió 10m",
        "sea_surface_temperature": "SST (Biển Đông)",
        "u_wind_850hpa": "U-Wind 850hPa",
        "v_wind_850hpa": "V-Wind 850hPa",
        "specific_humidity_850hpa": "Sp.Humidity 850hPa",
        "oni_anom": "ONI/ENSO Index",
    }

    bar_colors = [group_colors.get(g, "#8B949E") for g in mi_df["group"]]
    labels = [rename_display.get(f, f) for f in mi_df["feature"]]

    bars = ax1.barh(range(len(mi_df)), mi_df["mi_score"], color=bar_colors,
                    alpha=0.85, edgecolor="#0D1117", linewidth=0.5)

    ax1.set_yticks(range(len(mi_df)))
    ax1.set_yticklabels(labels, fontsize=10)
    ax1.set_xlabel("Mutual Information Score", fontsize=11)
    ax1.set_title("(a) Ranking đặc trưng theo Mutual Information", fontweight="bold")
    ax1.grid(True, alpha=0.3, axis="x")

    # Annotate scores
    for i, (bar, score) in enumerate(zip(bars, mi_df["mi_score"])):
        ax1.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2,
                 f"{score:.4f}", va="center", fontsize=9, color="#C9D1D9")

    # Legend for groups
    from matplotlib.patches import Patch
    legend_patches = [Patch(facecolor=color, edgecolor="#0D1117", label=group)
                      for group, color in group_colors.items()
                      if group in mi_df["group"].values]
    ax1.legend(handles=legend_patches, loc="lower right", fontsize=9)

    # --- (b) Analysis summary ---
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis("off")

    # Group-level analysis
    group_mi = mi_df.groupby("group")["mi_score"].agg(["mean", "sum", "max"])

    summary_lines = [
        "PHÂN TÍCH FEATURE IMPORTANCE",
        "─" * 42, "",
        "MI Score đo mức độ thông tin mà",
        "feature cung cấp cho việc dự đoán",
        "lượng mưa (phi tuyến, robust).", "",
        "─" * 42, "",
        "TỔNG KẾT THEO NHÓM:", "",
    ]

    for group in group_mi.index:
        summary_lines.append(f"  {group}:")
        summary_lines.append(f"    Mean MI:  {group_mi.loc[group, 'mean']:.4f}")
        summary_lines.append(f"    Total MI: {group_mi.loc[group, 'sum']:.4f}")
        summary_lines.append(f"    Max MI:   {group_mi.loc[group, 'max']:.4f}")
        summary_lines.append("")

    # Top features
    summary_lines.append("─" * 42)
    summary_lines.append("")
    summary_lines.append("TOP 3 FEATURES:")
    top3 = mi_df.nlargest(3, "mi_score")
    for _, row in top3.iterrows():
        name = rename_display.get(row["feature"], row["feature"])
        summary_lines.append(f"  1. {name}: {row['mi_score']:.4f}")

    summary_lines.append("")
    summary_lines.append("─" * 42)
    summary_lines.append("")
    summary_lines.append("→ Features với MI cao nhất nên")
    summary_lines.append("  được ưu tiên trong model.")
    summary_lines.append("  So sánh giữa nhóm bề mặt")
    summary_lines.append("  và ERA5 giúp quyết định")
    summary_lines.append("  có cần ERA5 cho 63 tỉnh không.")

    ax2.text(0.05, 0.95, "\n".join(summary_lines),
             transform=ax2.transAxes, fontsize=9, fontfamily="monospace",
             color="#C9D1D9", verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#0D1117",
                       edgecolor="#30363D", alpha=0.9))

    output_path = EDA_DIR / "08_feature_importance_mi.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  → Saved: %s", output_path)


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    """
    Hàm chính: Load dữ liệu, tạo 8 biểu đồ EDA.
    """
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU PHÂN TÍCH EDA — DỰ ĐOÁN MƯA ĐÀ NẴNG")
    logger.info("  Output directory: %s", EDA_DIR)
    logger.info("=" * 70)

    # Load data
    data = load_data()

    # Merge
    df = merge_for_eda(data)

    logger.info("")
    logger.info("Dataset cho EDA:")
    logger.info("  Shape: %s", df.shape)
    logger.info("  Columns: %s", list(df.columns))
    logger.info("  Date range: %s → %s", df["datetime"].iloc[0], df["datetime"].iloc[-1])
    logger.info("")

    # Tạo 8 biểu đồ
    logger.info("=" * 70)
    logger.info("ĐANG TẠO 8 BIỂU ĐỒ EDA...")
    logger.info("=" * 70)

    plot_01_target_distribution(df)
    plot_02_monthly_seasonality(df)
    plot_03_correlation_heatmap(df)
    plot_04_timeseries(df)
    plot_05_enso_impact(df)
    plot_06_diurnal_pattern(df)
    plot_07_lag_correlation(df)
    plot_08_feature_importance(df)

    logger.info("")
    logger.info("=" * 70)
    logger.info("HOÀN TẤT EDA! Tất cả biểu đồ đã lưu tại: %s", EDA_DIR)
    logger.info("=" * 70)

    # Liệt kê files
    for f in sorted(EDA_DIR.iterdir()):
        logger.info("  %s (%.1f KB)", f.name, f.stat().st_size / 1e3)


if __name__ == "__main__":
    main()
