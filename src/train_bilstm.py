"""Huấn luyện Bi-LSTM với trọng số mưa lớn và dừng sớm theo validation."""

from __future__ import annotations

import copy
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import torch

from .bilstm_model import BiLSTM

if TYPE_CHECKING:
    from torch.utils.data import DataLoader

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrainingConfig:
    max_epochs: int = 40
    patience: int = 7
    learning_rate: float = 0.001
    heavy_rain_threshold: float = 5.0  # mm/h
    heavy_rain_weight: float = 4.0
    seed: int = 42
    device: str = "auto"


@dataclass
class TrainingResult:
    model: BiLSTM
    history: list[dict[str, float]]
    best_epoch: int
    best_val_loss: float
    y_true: np.ndarray | None
    y_pred: np.ndarray | None
    device: str


def weighted_mse_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    *,
    threshold: float = 5.0,
    heavy_weight: float = 4.0,
) -> torch.Tensor:
    """Nhân trọng số cho từng giờ có mưa thực tế > ngưỡng.

    Áp dụng cùng một hàm trên train và validation để phép dừng sớm
    tối ưu đúng mục tiêu đánh giá. Nhãn ở đây là mm/h gốc, chưa scale.
    """
    if prediction.shape != target.shape:
        raise ValueError("Kích thước dự báo và nhãn phải trùng nhau")
    if heavy_weight < 1:
        raise ValueError("heavy_weight phải >= 1")
    weights = torch.where(target > threshold, heavy_weight, 1.0)
    return (weights * (prediction - target).square()).mean()


def _select_device(choice: str) -> torch.device:
    if choice == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(choice)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Đã yêu cầu CUDA nhưng máy hiện không có CUDA")
    return device


def _epoch_loss(
    model: BiLSTM,
    loader: DataLoader,
    device: torch.device,
    config: TrainingConfig,
    optimizer: torch.optim.Optimizer | None,
) -> float:
    is_training = optimizer is not None
    model.train(is_training)
    loss_total = 0.0
    count = 0
    for x, y in loader:
        x = x.to(device=device, dtype=torch.float32)
        y = y.to(device=device, dtype=torch.float32)
        if is_training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(is_training):
            prediction = model(x)
            loss = weighted_mse_loss(
                prediction,
                y,
                threshold=config.heavy_rain_threshold,
                heavy_weight=config.heavy_rain_weight,
            )
            if is_training:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
        batch_size = x.shape[0]
        loss_total += float(loss.detach()) * batch_size
        count += batch_size
    if count == 0:
        raise ValueError("DataLoader rỗng; hãy kiểm tra split, mốc thiếu và cửa sổ 24+6 giờ")
    return loss_total / count


def predict(model: BiLSTM, loader: DataLoader, device: str | torch.device) -> tuple[np.ndarray, np.ndarray]:
    """Giữ nguyên thứ tự của test_loader để ghép dự báo với timestamp."""
    model.eval()
    actual, predicted = [], []
    with torch.no_grad():
        for x, y in loader:
            # Lượng mưa vật lý không âm; chỉ chặn ở bước suy luận, không thay
            # đổi gradient của kiến trúc Linear → ReLU → Linear được yêu cầu.
            predicted.append(model(x.to(device=device, dtype=torch.float32)).cpu().numpy().clip(min=0))
            actual.append(y.numpy())
    if not actual:
        raise ValueError("test_loader rỗng")
    return np.concatenate(actual), np.concatenate(predicted)


def train_bilstm(
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader | None,
    *,
    feature_cols: list[str],
    checkpoint_path: str | Path = "models/best_bilstm_model.pth",
    config: TrainingConfig | None = None,
) -> TrainingResult:
    """Fit bằng train/validation; có thể trì hoãn dự báo test đến sau chọn model."""
    config = config or TrainingConfig()
    if config.max_epochs < 1 or config.patience < 1:
        raise ValueError("max_epochs và patience phải lớn hơn 0")
    random.seed(config.seed)
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)

    device = _select_device(config.device)
    output_dim = int(val_loader.dataset[0][1].shape[0])
    model = BiLSTM(input_dim=len(feature_cols), output_dim=output_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    checkpoint_path = Path(checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    best_val = float("inf")
    best_epoch = 0
    best_state = None
    no_improvement = 0
    history: list[dict[str, float]] = []

    for epoch in range(1, config.max_epochs + 1):
        train_loss = _epoch_loss(model, train_loader, device, config, optimizer)
        val_loss = _epoch_loss(model, val_loader, device, config, None)
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
        LOGGER.info("Epoch %02d | train %.4f | validation %.4f", epoch, train_loss, val_loss)

        if val_loss < best_val - 1e-8:
            best_val = val_loss
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            no_improvement = 0
            torch.save(
                {
                    "model_state_dict": best_state,
                    "input_dim": len(feature_cols),
                    "output_dim": output_dim,
                    "feature_cols": list(feature_cols),
                    "best_epoch": best_epoch,
                    "best_val_loss": best_val,
                    "training_config": vars(config),
                },
                checkpoint_path,
            )
        else:
            no_improvement += 1
            if no_improvement >= config.patience:
                LOGGER.info("Dừng sớm sau %d epoch không cải thiện.", config.patience)
                break

    if best_state is None:
        raise RuntimeError("Huấn luyện không tạo được checkpoint hợp lệ")
    model.load_state_dict(best_state)
    y_true, y_pred = predict(model, test_loader, device) if test_loader is not None else (None, None)
    return TrainingResult(model, history, best_epoch, best_val, y_true, y_pred, str(device))
