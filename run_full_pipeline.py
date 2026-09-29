"""Chạy hợp nhất dữ liệu → đặc trưng → Bi-LSTM → đánh giá/bốn đồ thị.

Ví dụ:
    python run_full_pipeline.py
    python run_full_pipeline.py --prepare-only
    python run_full_pipeline.py --max-epochs 2 --batch-size 512
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

from src.merge_raw_data import merge_raw_data
from src.feature_engineering import engineer_features

ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger(__name__)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline dự báo mưa Đà Nẵng 1–6 giờ")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw_data")
    parser.add_argument("--max-interp-hours", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--max-epochs", type=int, default=40)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--prepare-only", action="store_true",
                        help="Chỉ hợp nhất, tạo đặc trưng và kiểm tra cửa sổ; chưa huấn luyện")
    parser.add_argument("--reuse-merged", action="store_true",
                        help="Dùng master Parquet sẵn có để chạy lại train nhanh hơn")
    parser.add_argument("--include-retrospective-oni", action="store_true",
                        help="Dùng ONI hồi cứu trong mô hình; không đại diện chạy thời gian thực")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    # Windows thường mặc định cp1252; giữ log tiếng Việt đọc được ở console.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.max_interp_hours < 0:
        raise ValueError("--max-interp-hours phải >= 0")

    processed_dir = ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    master_path = processed_dir / "danang_master_merged.parquet"
    if args.reuse_merged:
        if not master_path.exists():
            raise FileNotFoundError(f"--reuse-merged cần file {master_path}")
        LOGGER.info("Giai đoạn 0: dùng master đã kiểm tra tại %s", master_path)
        merged = pd.read_parquet(master_path)
    else:
        LOGGER.info("Giai đoạn 0: hợp nhất nguồn tại %s", args.raw_dir)
        merged = merge_raw_data(
            raw_dir=args.raw_dir,
            output_dir=processed_dir,
            max_interp_hours=args.max_interp_hours,
        )
    LOGGER.info("Giai đoạn 1: tạo đặc trưng và kiểm tra cửa sổ")
    engineered = engineer_features(merged)
    feature_path = processed_dir / "danang_features.parquet"
    engineered.to_parquet(feature_path, index=False)

    # Dataset cũng dùng PyTorch, nên cả chế độ chuẩn bị dữ liệu cần đủ thư viện.
    from src.dataset_prep import prepare_datasets

    prepared = prepare_datasets(
        engineered,
        input_length=24,
        output_length=6,
        batch_size=args.batch_size,
        scaler_path=ROOT / "models" / "scaler.pkl",
        include_retrospective_oni=args.include_retrospective_oni,
    )
    diagnostic_path = processed_dir / "window_diagnostics.json"
    diagnostic_path.write_text(
        json.dumps(
            {
                **prepared.diagnostics,
                "train_end": str(prepared.split_boundaries["train_end"]),
                "val_end": str(prepared.split_boundaries["val_end"]),
                "features": prepared.feature_cols,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    LOGGER.info("Đã lưu chẩn đoán vào %s", diagnostic_path)
    if args.prepare_only:
        LOGGER.info("Dừng theo --prepare-only. Có thể chạy lại không có cờ này để train.")
        return

    from src.train_bilstm import TrainingConfig, train_bilstm
    from src.visualize_and_evaluate import evaluate_and_visualize

    LOGGER.info("Giai đoạn 2: huấn luyện Bi-LSTM")
    training = train_bilstm(
        prepared.train_loader,
        prepared.val_loader,
        prepared.test_loader,
        feature_cols=prepared.feature_cols,
        checkpoint_path=ROOT / "models" / "best_bilstm_model.pth",
        config=TrainingConfig(max_epochs=args.max_epochs, device=args.device),
    )
    LOGGER.info("Checkpoint tốt nhất: epoch %d, val loss %.4f", training.best_epoch,
                training.best_val_loss)
    LOGGER.info("Thiết bị huấn luyện: %s", training.device)

    LOGGER.info("Giai đoạn 3: đánh giá và vẽ bốn đồ thị")
    metrics = evaluate_and_visualize(
        engineered,
        training.history,
        training.y_true,
        training.y_pred,
        prepared.test_dataset.target_datetimes,
        output_dir=ROOT / "plots",
    )
    (ROOT / "plots" / "test_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "models" / "training_summary.json").write_text(
        json.dumps({
            "device": training.device,
            "best_epoch": training.best_epoch,
            "best_val_loss": training.best_val_loss,
            "epochs_ran": len(training.history),
            "feature_count": len(prepared.feature_cols),
            "train_windows": prepared.diagnostics["train_windows"],
            "val_windows": prepared.diagnostics["val_windows"],
            "test_windows": prepared.diagnostics["test_windows"],
        }, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    LOGGER.info("Hoàn thành pipeline.")


if __name__ == "__main__":
    main()
