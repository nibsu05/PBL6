import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import os
import torch
import json
import numpy as np
import logging
from pathlib import Path
import sys

from experiments.informer_ablation_config import get_experiment, list_experiments
from src.informer_dataset import prepare_informer_data
from src.informer.model import Informer
from src.train_informer import train_informer, InformerTrainingConfig
from src.informer_evaluate import evaluate_experiment, compare_experiments

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_single_experiment(exp_name: str, device: str):
    config = get_experiment(exp_name)
    logger.info(f"=== Bắt đầu chạy: {exp_name} ===")
    logger.info(f"Mô tả: {config.description}")
    
    # 1. Chuẩn bị dữ liệu
    data_path = os.path.join("data", "processed", "danang_full_features_2021_2026.csv")
    prepared_data = prepare_informer_data(
        data_path=data_path,
        feature_cols=config.feature_cols,
        seq_len=config.seq_len,
        label_len=config.label_len,
        pred_len=config.pred_len,
        batch_size=config.batch_size,
    )
    
    actual_features = prepared_data.feature_cols
    enc_in = len(actual_features)
    dec_in = len(actual_features)
    c_out = 1  # Chỉ dự báo precipitation
    
    # 2. Khởi tạo mô hình
    model = Informer(
        enc_in=enc_in,
        dec_in=dec_in,
        c_out=c_out,
        seq_len=config.seq_len,
        label_len=config.label_len,
        pred_len=config.pred_len,
        factor=config.factor,
        d_model=config.d_model,
        n_heads=config.n_heads,
        e_layers=config.e_layers,
        d_layers=config.d_layers,
        d_ff=config.d_ff,
        dropout=config.dropout,
        attn='prob',
        embed_type='timeF',
        freq='h',
        activation=config.activation,
        distil=config.distil,
    )
    
    # 3. Huấn luyện
    train_config = InformerTrainingConfig(
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        max_epochs=config.max_epochs,
        patience=config.patience,
        device=device,
        save_dir=os.path.join("models", "informer"),
        experiment_name=exp_name
    )
    
    result = train_informer(
        train_loader=prepared_data.train_loader,
        val_loader=prepared_data.val_loader,
        test_loader=prepared_data.test_loader,
        model=model,
        config=train_config,
        feature_cols=actual_features
    )
    
    # 4. Đánh giá
    logger.info("Đánh giá mô hình...")
    metrics = evaluate_experiment(
        y_true=result.y_true_test,
        y_pred=result.y_pred_test,
        pred_len=config.pred_len,
        target_scaler=None,  # y đã ở đơn vị gốc mm/h, không cần inverse transform
    )
    
    # 5. Lưu kết quả
    res_dir = Path("experiments") / "results" / exp_name
    res_dir.mkdir(parents=True, exist_ok=True)
    
    with open(res_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
        
    with open(res_dir / "training_log.json", "w", encoding="utf-8") as f:
        json.dump(result.history, f, indent=4)
        
    np.savez_compressed(
        res_dir / "predictions.npz",
        y_true=result.y_true_test,
        y_pred=result.y_pred_test
    )
    
    logger.info(f"Đã lưu kết quả tại {res_dir}")
    logger.info(f"=== Hoàn thành: {exp_name} ===\n")

def main():
    parser = argparse.ArgumentParser(description="Run Informer Ablation Experiments")
    parser.add_argument("--experiment", type=str, help="Tên experiment hoặc 'all'")
    parser.add_argument("--compare", action="store_true", help="So sánh các experiment đã chạy")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    
    args = parser.parse_args()
    
    if args.compare:
        compare_experiments(os.path.join("experiments", "results"))
        return
        
    if not args.experiment:
        parser.print_help()
        return
        
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
    torch.manual_seed(42)
    np.random.seed(42)
        
    if args.experiment.lower() == "all":
        exps = list_experiments()
        for exp in exps:
            run_single_experiment(exp, device)
    else:
        run_single_experiment(args.experiment, device)

if __name__ == "__main__":
    main()
