# ==============================================================================
# visualize_poc_reports.py — Xuất 4 biểu đồ báo cáo Giáo sư
# ==============================================================================
"""
Module 5: Xuất 4 biểu đồ chất lượng cao (300 DPI) từ tập dữ liệu PoC.
Output folder: poc/plots/

1. plot1_correlation_heatmap.png
2. plot2_diurnal_seasonal_cycle.png
3. plot3_extreme_rain_violin.png
4. plot4_case_study_2025_2026.png

Sử dụng:
  python visualize_poc_reports.py
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
POC_DATASET = DATASETS_DIR / "dataset_poc_2025_2026.parquet"
PLOTS_DIR = BASE_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Cấu hình matplotlib (White background)
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({
    "font.size": 12,
    "axes.titlesize": 16,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "figure.titlesize": 18,
})


def plot_1_correlation_heatmap(df: pd.DataFrame):
    logger.info("Generating Plot 1: Correlation Heatmap...")
    # Chọn các features quan trọng (loại bỏ những cột không phải numeric hoặc không cần thiết)
    features = [
        "precipitation", "wind_speed_10m", "temperature_2m", 
        "sea_surface_temperature", "wind_speed_850", "sst_air_temp_diff",
        "precip_lag_1h", "precip_lag_6h", "precip_roll_sum_24h", "oni_anom"
    ]
    # Chỉ giữ những cột tồn tại trong df
    features = [f for f in features if f in df.columns]
    
    corr = df[features].corr(method="spearman")
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, 
                square=True, linewidths=.5, cbar_kws={"shrink": .8}, ax=ax)
    
    ax.set_title("Spearman Correlation Heatmap (PoC Dataset)", pad=20)
    plt.tight_layout()
    output_path = PLOTS_DIR / "plot1_correlation_heatmap.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("  -> Saved %s", output_path.name)


def plot_2_diurnal_seasonal_cycle(df: pd.DataFrame):
    logger.info("Generating Plot 2: Diurnal & Seasonal Cycle...")
    if "hour" not in df.columns:
        df["hour"] = df["datetime"].dt.hour
    if "month" not in df.columns:
        df["month"] = df["datetime"].dt.month
        
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 24-hour cycle
    hourly_mean = df.groupby("hour")["precipitation"].mean()
    ax1.plot(hourly_mean.index, hourly_mean.values, marker="o", color="#3498db", linewidth=2)
    ax1.set_title("Diurnal Cycle (UTC+7)")
    ax1.set_xlabel("Hour of Day")
    ax1.set_ylabel("Mean Precipitation (mm/h)")
    ax1.set_xticks(range(0, 24, 2))
    ax1.grid(True, alpha=0.3)
    
    # 12-month cycle
    monthly_mean = df.groupby("month")["precipitation"].mean()
    ax2.plot(monthly_mean.index, monthly_mean.values, marker="s", color="#e74c3c", linewidth=2)
    ax2.set_title("Seasonal Cycle")
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Mean Precipitation (mm/h)")
    ax2.set_xticks(range(1, 13))
    ax2.grid(True, alpha=0.3)
    
    fig.suptitle("Precipitation Cycles in Da Nang", y=1.05)
    plt.tight_layout()
    output_path = PLOTS_DIR / "plot2_diurnal_seasonal_cycle.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("  -> Saved %s", output_path.name)


def plot_3_extreme_rain_violin(df: pd.DataFrame):
    logger.info("Generating Plot 3: Extreme Rain Violin...")
    
    # Phân loại
    df["rain_class"] = "Normal Rain"
    df.loc[df["precipitation"] == 0, "rain_class"] = "No Rain"
    df.loc[df["precipitation"] > 30, "rain_class"] = "Extreme Rain (>30mm)"
    
    # Bỏ đi Normal Rain để dễ nhìn so sánh No Rain vs Extreme
    df_plot = df[df["rain_class"].isin(["No Rain", "Extreme Rain (>30mm)"])]
    
    features = ["wind_speed_850", "sst_air_temp_diff", "sea_surface_temperature"]
    features = [f for f in features if f in df.columns]
    
    if not features:
        logger.warning("No physical features found for Plot 3. Skipping.")
        return

    fig, axes = plt.subplots(1, len(features), figsize=(6 * len(features), 6))
    if len(features) == 1:
        axes = [axes]
        
    for i, feature in enumerate(features):
        sns.violinplot(data=df_plot, x="rain_class", y=feature, ax=axes[i], 
                       palette=["#95a5a6", "#e74c3c"], inner="quartile")
        axes[i].set_title(f"Distribution of {feature}")
        axes[i].set_xlabel("")
        axes[i].set_ylabel(feature)
        
    fig.suptitle("Comparison: Extreme Rain vs No Rain", y=1.05)
    plt.tight_layout()
    output_path = PLOTS_DIR / "plot3_extreme_rain_violin.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("  -> Saved %s", output_path.name)


def plot_4_case_study(df: pd.DataFrame):
    logger.info("Generating Plot 4: Case Study 2025-2026...")
    
    # Tìm đợt mưa lớn nhất
    max_rain_idx = df["precipitation"].idxmax()
    peak_time = df.loc[max_rain_idx, "datetime"]
    
    # Lấy dữ liệu +- 3 ngày (72 giờ) xung quanh peak
    start_time = peak_time - pd.Timedelta(days=3)
    end_time = peak_time + pd.Timedelta(days=3)
    
    mask = (df["datetime"] >= start_time) & (df["datetime"] <= end_time)
    df_case = df[mask].copy()
    
    if df_case.empty:
        logger.warning("Could not extract case study window. Skipping Plot 4.")
        return
        
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    
    # 1. Precipitation
    axes[0].bar(df_case["datetime"], df_case["precipitation"], width=0.04, color="#3498db")
    axes[0].set_ylabel("Rain (mm/h)")
    axes[0].set_title(f"Heavy Rain Event Case Study (Peak: {peak_time.strftime('%Y-%m-%d %H:%M')})")
    axes[0].grid(True, alpha=0.3)
    
    # 2. SST
    if "sea_surface_temperature" in df_case.columns:
        axes[1].plot(df_case["datetime"], df_case["sea_surface_temperature"], color="#e74c3c", linewidth=2)
        axes[1].set_ylabel("SST (°C)")
        axes[1].grid(True, alpha=0.3)
        
    # 3. Wind Speed 850
    if "wind_speed_850" in df_case.columns:
        axes[2].plot(df_case["datetime"], df_case["wind_speed_850"], color="#2ecc71", linewidth=2)
        axes[2].set_ylabel("Wind 850hPa (m/s)")
        axes[2].grid(True, alpha=0.3)
        
    # 4. Surface Pressure
    if "surface_pressure" in df_case.columns:
        axes[3].plot(df_case["datetime"], df_case["surface_pressure"], color="#f39c12", linewidth=2)
        axes[3].set_ylabel("Pressure (hPa)")
        axes[3].grid(True, alpha=0.3)
        
    axes[3].set_xlabel("Time (UTC+7)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    output_path = PLOTS_DIR / "plot4_case_study_2025_2026.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info("  -> Saved %s", output_path.name)


def main():
    logger.info("=" * 70)
    logger.info("VISUALIZE PoC REPORTS (Module 5)")
    logger.info("=" * 70)
    
    if not POC_DATASET.exists():
        logger.error("PoC dataset not found: %s", POC_DATASET)
        sys.exit(1)
        
    df = pd.read_parquet(POC_DATASET)
    logger.info("Loaded PoC dataset: %s", df.shape)
    
    plot_1_correlation_heatmap(df)
    plot_2_diurnal_seasonal_cycle(df)
    plot_3_extreme_rain_violin(df)
    plot_4_case_study(df)
    
    logger.info("All plots generated in %s", PLOTS_DIR)

if __name__ == "__main__":
    main()
