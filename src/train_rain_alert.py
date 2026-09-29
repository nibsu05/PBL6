"""Huấn luyện mô hình hai đầu trên train/validation, trì hoãn test."""

from __future__ import annotations

import copy
import logging
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .rain_alert_model import RainAlertBiLSTM, RainAlertConfig, rain_alert_loss

LOGGER = logging.getLogger(__name__)


def predict_alert(model: RainAlertBiLSTM, loader: DataLoader,
                  device: torch.device) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    observed, amounts, probabilities = [], [], []
    with torch.no_grad():
        for x, y in loader:
            amount, logit = model(x.to(device, dtype=torch.float32))
            observed.append(y.numpy())
            amounts.append(amount.cpu().numpy())
            probabilities.append(logit.sigmoid().cpu().numpy())
    if not observed:
        raise ValueError("DataLoader rỗng")
    return np.concatenate(observed), np.concatenate(amounts), np.concatenate(probabilities)


def fit_alert_model(train_loader: DataLoader, val_loader: DataLoader, *,
                    feature_cols: list[str], checkpoint_path: Path, device: torch.device,
                    config: RainAlertConfig) -> tuple[RainAlertBiLSTM, list[dict], int]:
    if config.max_epochs < 1 or config.patience < 1:
        raise ValueError("max_epochs và patience phải dương")
    random.seed(config.seed)
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)
    output_dim = int(val_loader.dataset[0][1].shape[0])
    model = RainAlertBiLSTM(input_dim=len(feature_cols), output_dim=output_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    best_loss, best_epoch, best_state, stale = float("inf"), 0, None, 0
    history: list[dict] = []
    for epoch in range(1, config.max_epochs + 1):
        metrics: dict[str, float] = {"epoch": epoch}
        for phase, loader in (("train", train_loader), ("validation", val_loader)):
            training = phase == "train"
            model.train(training)
            total, count = 0.0, 0
            for x, y in loader:
                x = x.to(device, dtype=torch.float32)
                y = y.to(device, dtype=torch.float32)
                if training:
                    optimizer.zero_grad(set_to_none=True)
                with torch.set_grad_enabled(training):
                    amount, logit = model(x)
                    loss, _ = rain_alert_loss(amount, logit, y, config)
                    if training:
                        loss.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                        optimizer.step()
                total += float(loss.detach()) * len(x)
                count += len(x)
            if count == 0:
                raise ValueError(f"{phase} không có cửa sổ hợp lệ")
            metrics[f"{phase}_loss"] = total / count
        history.append(metrics)
        LOGGER.info("Epoch %02d | train %.4f | validation %.4f", epoch,
                    metrics["train_loss"], metrics["validation_loss"])
        if metrics["validation_loss"] < best_loss - 1e-8:
            best_loss = metrics["validation_loss"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            stale = 0
            torch.save({
                "model_state_dict": best_state,
                "feature_cols": feature_cols,
                "input_dim": len(feature_cols),
                "output_dim": output_dim,
                "best_epoch": best_epoch,
                "best_validation_loss": best_loss,
                "training_config": vars(config),
            }, checkpoint_path)
        else:
            stale += 1
            if stale >= config.patience:
                LOGGER.info("Dừng sớm sau %d epoch không cải thiện", config.patience)
                break
    if best_state is None:
        raise RuntimeError("Không tạo được checkpoint")
    model.load_state_dict(best_state)
    return model, history, best_epoch
