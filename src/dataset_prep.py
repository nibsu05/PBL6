"""Chia dữ liệu theo thời gian và tạo cửa sổ PyTorch 24 giờ → 6 giờ.

Ranh giới train/validation/test được tính trên *thời gian thực* của chuỗi,
không tính theo số hàng còn lại sau khi thiếu ERA5. Một cửa sổ chỉ hợp lệ khi
toàn bộ đầu vào và cả sáu nhãn liên tiếp từng giờ, có đầy đủ đặc trưng.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import RobustScaler
from torch.utils.data import DataLoader, Dataset

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOUR_NS = 3_600_000_000_000

# Chỉ chọn biến đã biết tại thời điểm quan sát. Không tự động lấy mọi cột số,
# vì tập đầu vào sau này có thể chứa nhãn tương lai hoặc cột đánh giá. ONI
# hồi cứu được giữ trong danh sách nhưng mặc định loại khỏi đầu vào thực thời.
BASE_FEATURES = (
    "temperature_2m", "relative_humidity_2m", "surface_pressure",
    "wind_speed_10m", "wind_direction_10m", "precipitation",
    "sea_surface_temperature", "u_850", "v_850", "specific_humidity_850",
    "cape", "cin", "tcwv", "oni",
)
ENGINEERED_FEATURES = (
    "sin_hour", "cos_hour", "sin_month", "cos_month",
    *(f"precip_lag_{lag}h" for lag in (1, 2, 3, 6, 12, 24)),
    *(f"{name}_lag_{lag}h"
      for name in ("relative_humidity_2m", "specific_humidity_850")
      for lag in (1, 3, 6)),
    *(f"precip_roll_sum_{window}h" for window in (3, 6, 24)),
    "wind_speed_850", "sst_air_temp_diff",
)


class TimeSeriesWindowDataset(Dataset):
    """Đọc cửa sổ theo chỉ số; không nhân bản toàn bộ chuỗi vào RAM."""

    def __init__(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        timestamps: pd.DatetimeIndex,
        starts: np.ndarray,
        input_length: int,
        output_length: int,
    ) -> None:
        self.features = features
        self.targets = targets
        self.timestamps = timestamps
        self.starts = np.asarray(starts, dtype=np.int64)
        self.input_length = input_length
        self.output_length = output_length

    def __len__(self) -> int:
        return len(self.starts)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        start = int(self.starts[index])
        target_start = start + self.input_length
        x = self.features[start:target_start]
        y = self.targets[target_start:target_start + self.output_length]
        return torch.from_numpy(x), torch.from_numpy(y)

    @property
    def anchor_datetimes(self) -> pd.DatetimeIndex:
        """Giờ quan sát cuối cùng của từng cửa sổ."""
        return self.timestamps.take(self.starts + self.input_length - 1)

    @property
    def target_datetimes(self) -> pd.DataFrame:
        """Giờ nhãn t+1..t+6 (UTC+7), cùng thứ tự với DataLoader không shuffle."""
        return pd.DataFrame({
            f"t+{h}": self.timestamps.take(self.starts + self.input_length + h - 1).array
            for h in range(1, self.output_length + 1)
        })


@dataclass(frozen=True)
class PreparedData:
    """Các đối tượng cần dùng cho huấn luyện, kiểm định và vẽ đồ thị."""

    feature_cols: list[str]
    train_loader: DataLoader
    val_loader: DataLoader
    test_loader: DataLoader
    train_dataset: TimeSeriesWindowDataset
    val_dataset: TimeSeriesWindowDataset
    test_dataset: TimeSeriesWindowDataset
    scaler: RobustScaler
    split_boundaries: dict[str, pd.Timestamp]
    diagnostics: dict[str, int | str]


def _window_starts(
    times_ns: np.ndarray,
    finite_rows: np.ndarray,
    window_length: int,
) -> tuple[np.ndarray, dict[str, int]]:
    """Tìm nhanh các cửa sổ không chứa lỗ thời gian hoặc giá trị khuyết."""
    n_candidates = len(times_ns) - window_length + 1
    if n_candidates <= 0:
        raise ValueError(f"Cần ít nhất {window_length} giờ dữ liệu.")
    starts = np.arange(n_candidates, dtype=np.int64)

    bad_edges = np.diff(times_ns) != HOUR_NS
    edge_prefix = np.r_[0, np.cumsum(bad_edges, dtype=np.int64)]
    contiguous = edge_prefix[starts + window_length - 1] == edge_prefix[starts]

    invalid_prefix = np.r_[0, np.cumsum(~finite_rows, dtype=np.int64)]
    complete = invalid_prefix[starts + window_length] == invalid_prefix[starts]
    diagnostics = {
        "candidate_windows": int(n_candidates),
        "windows_with_time_gap": int((~contiguous).sum()),
        "windows_with_missing_value": int((~complete).sum()),
    }
    return starts[contiguous & complete], diagnostics


def prepare_datasets(
    df: pd.DataFrame,
    *,
    input_length: int = 24,
    output_length: int = 6,
    batch_size: int = 256,
    scaler_path: str | Path | None = "models/scaler.pkl",
    train_fraction: float = 0.70,
    val_fraction: float = 0.15,
    shuffle_train: bool = True,
    include_retrospective_oni: bool = False,
) -> PreparedData:
    """Fit RobustScaler trên train và trả về ba DataLoader không leakage.

    Split xét *toàn bộ* giờ nhãn: t+1..t+6 phải nằm trong cùng một tập.
    Input validation/test được phép nhìn lại giờ thuộc tập trước, vì tại lúc
    dự báo những quan sát quá khứ đó đã có thật. Scaler không fit các giờ này.
    File ONI theo tháng thường ghi giá trị hồi cứu vào đầu tháng, trước ngày
    NOAA công bố; mặc định loại ONI khỏi X. Bật ``include_retrospective_oni``
    chỉ khi nghiên cứu hindcast và nêu rõ giới hạn này trong báo cáo.
    """
    if df.empty or "datetime" not in df or "precipitation" not in df:
        raise ValueError("Cần DataFrame có datetime và precipitation.")
    if input_length < 1 or output_length < 1 or batch_size < 1:
        raise ValueError("input_length, output_length và batch_size phải dương.")
    if not (0 < train_fraction < 1 and 0 < val_fraction < 1
            and train_fraction + val_fraction < 1):
        raise ValueError("Tỷ lệ train/validation phải dương và có tổng < 1.")

    frame = df.copy().sort_values("datetime").reset_index(drop=True)
    times = pd.DatetimeIndex(pd.to_datetime(frame["datetime"], errors="raise"))
    if times.tz is None:
        raise ValueError("Datetime phải có timezone; hãy chạy engineer_features trước.")
    times = times.tz_convert("Asia/Ho_Chi_Minh")
    if times.has_duplicates or not (times == times.floor("h")).all():
        raise ValueError("Datetime phải duy nhất và nằm đúng đầu giờ.")

    # Mỗi feature phải có ít nhất một giá trị hợp lệ trong train. ERA5 chưa tải
    # CAPE/CIN/TCWV thì các cột này được bỏ và ghi rõ trong diagnostics.
    total_hours = int((times[-1].value - times[0].value) // HOUR_NS) + 1
    train_cut = times[0] + pd.Timedelta(hours=int(total_hours * train_fraction))
    val_cut = times[0] + pd.Timedelta(hours=int(total_hours * (train_fraction + val_fraction)))
    if train_cut <= times[0] or val_cut <= train_cut or val_cut > times[-1]:
        raise ValueError("Chuỗi quá ngắn để chia thời gian 70/15/15.")

    if include_retrospective_oni and "oni" in frame:
        LOGGER.warning("Dùng ONI hồi cứu: chỉ phù hợp thí nghiệm hindcast, không phải dự báo real-time.")
    elif "oni" in frame:
        LOGGER.info("Loại ONI hồi cứu khỏi X vì chưa có thời điểm công bố NOAA.")
    possible = [
        c for c in BASE_FEATURES + ENGINEERED_FEATURES
        if c in frame.columns and (c != "oni" or include_retrospective_oni)
    ]
    numeric = frame[possible].apply(pd.to_numeric, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    train_rows = times < train_cut
    feature_cols = [c for c in possible if numeric.loc[train_rows, c].notna().any()]
    omitted = [c for c in possible if c not in feature_cols]
    if omitted:
        LOGGER.warning("Bỏ đặc trưng không có dữ liệu train: %s", ", ".join(omitted))
    if "precipitation" not in feature_cols:
        raise ValueError("Không có lượng mưa hợp lệ trong khoảng train.")

    numeric = numeric[feature_cols]
    target = pd.to_numeric(frame["precipitation"], errors="coerce").to_numpy(dtype=np.float64)
    valid_rows = np.isfinite(numeric.to_numpy(dtype=np.float64)).all(axis=1)
    valid_rows &= np.isfinite(target) & (target >= 0)

    fit_rows = train_rows & valid_rows
    if not fit_rows.any():
        raise ValueError("Không có hàng train đầy đủ để fit RobustScaler.")
    scaler = RobustScaler()
    scaler.fit(numeric.loc[fit_rows, feature_cols])

    # Transform chỉ những hàng hợp lệ. NaN ở giờ thiếu được giữ để không bao
    # giờ vô tình tạo đầu vào số giả cho cửa sổ đi qua gap dữ liệu.
    x_scaled = np.full((len(frame), len(feature_cols)), np.nan, dtype=np.float32)
    x_scaled[valid_rows] = scaler.transform(numeric.loc[valid_rows, feature_cols]).astype(np.float32)
    y = target.astype(np.float32)

    # Pandas 3 có thể lưu DatetimeIndex ở đơn vị micro giây. Ép về nano giây
    # trước khi so với HOUR_NS và Timestamp.value, vốn luôn là nano giây.
    times_ns = times.as_unit("ns").asi8
    starts, window_info = _window_starts(times_ns, valid_rows, input_length + output_length)
    first_target_ns = times_ns[starts + input_length]
    last_target_ns = times_ns[starts + input_length + output_length - 1]
    train_starts = starts[last_target_ns < train_cut.value]
    val_starts = starts[(first_target_ns >= train_cut.value) & (last_target_ns < val_cut.value)]
    test_starts = starts[first_target_ns >= val_cut.value]

    diagnostics: dict[str, int | str] = {
        "total_rows": len(frame),
        # Sau engineer_features, giờ vắng mặt đã thành hàng NaN nên độ dài
        # DataFrame một mình không còn phản ánh được số giờ thiếu ban đầu.
        "calendar_missing_hours": max(
            total_hours - len(frame),
            int(frame[[c for c in ("precipitation", "temperature_2m", "relative_humidity_2m")
                       if c in frame]].isna().all(axis=1).sum()),
        ),
        "hours_without_precipitation": int(np.isnan(target).sum()),
        "invalid_rows": int((~valid_rows).sum()),
        "train_scaler_rows": int(fit_rows.sum()),
        "omitted_features": ", ".join(omitted),
        "oni_excluded_realtime": int("oni" in frame and not include_retrospective_oni),
        **window_info,
        "windows_crossing_split": int(len(starts) - len(train_starts) - len(val_starts) - len(test_starts)),
        "train_windows": len(train_starts),
        "val_windows": len(val_starts),
        "test_windows": len(test_starts),
    }
    LOGGER.info("Chẩn đoán cửa sổ dữ liệu: %s", diagnostics)
    if not all((len(train_starts), len(val_starts), len(test_starts))):
        raise ValueError(f"Một tập không có cửa sổ hợp lệ; kiểm tra ERA5/gap: {diagnostics}")

    def dataset(indices: np.ndarray) -> TimeSeriesWindowDataset:
        return TimeSeriesWindowDataset(x_scaled, y, times, indices, input_length, output_length)

    train_ds, val_ds, test_ds = map(dataset, (train_starts, val_starts, test_starts))
    # Pinned CPU memory tăng hiệu quả truyền batch lên GPU khi CUDA khả dụng.
    pin_memory = torch.cuda.is_available()
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=shuffle_train,
                              num_workers=0, pin_memory=pin_memory)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=0, pin_memory=pin_memory)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                             num_workers=0, pin_memory=pin_memory)

    if scaler_path is not None:
        destination = Path(scaler_path)
        if not destination.is_absolute():
            destination = PROJECT_ROOT / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(scaler, destination)
        LOGGER.info("Đã lưu RobustScaler vào %s", destination)

    return PreparedData(
        feature_cols=feature_cols,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        train_dataset=train_ds,
        val_dataset=val_ds,
        test_dataset=test_ds,
        scaler=scaler,
        split_boundaries={"train_end": train_cut, "val_end": val_cut},
        diagnostics=diagnostics,
    )
