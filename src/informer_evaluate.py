import numpy as np
import pandas as pd
import json
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import pearsonr
import logging

logger = logging.getLogger(__name__)

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Tính các metric cơ bản trên dữ liệu làm phẳng"""
    y_t = y_true.flatten()
    y_p = y_pred.flatten()
    
    mae = mean_absolute_error(y_t, y_p)
    rmse = np.sqrt(mean_squared_error(y_t, y_p))
    r2 = r2_score(y_t, y_p)
    
    # Pearson correlation
    if np.std(y_t) == 0 or np.std(y_p) == 0:
        cc = 0.0
    else:
        cc, _ = pearsonr(y_t, y_p)
        
    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "R2": float(r2),
        "CC": float(cc)
    }

def compute_horizon_metrics(y_true: np.ndarray, y_pred: np.ndarray, pred_len: int) -> dict:
    """Tính metric cho từng thời điểm (horizon)"""
    horizons = [1, 3, 6, 12, 24]
    results = {}
    
    for h in horizons:
        if h <= pred_len:
            # Chọn cột thứ h-1
            y_t = y_true[:, h-1]
            y_p = y_pred[:, h-1]
            mae = mean_absolute_error(y_t, y_p)
            rmse = np.sqrt(mean_squared_error(y_t, y_p))
            results[f"t+{h}"] = {
                "MAE": float(mae),
                "RMSE": float(rmse)
            }
            
    return results

def compute_event_metrics(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 5.0) -> dict:
    """Tính CSI, POD, FAR cho sự kiện mưa lớn"""
    y_t = y_true.flatten()
    y_p = y_pred.flatten()
    
    hits = np.sum((y_t >= threshold) & (y_p >= threshold))
    misses = np.sum((y_t >= threshold) & (y_p < threshold))
    false_alarms = np.sum((y_t < threshold) & (y_p >= threshold))
    
    pod = hits / (hits + misses) if (hits + misses) > 0 else 0.0
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else 0.0
    csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) > 0 else 0.0
    
    return {
        "POD": float(pod),
        "FAR": float(far),
        "CSI": float(csi)
    }

def evaluate_experiment(y_true: np.ndarray, y_pred: np.ndarray, pred_len: int, target_scaler=None) -> dict:
    """Đánh giá toàn diện và trả về dict chứa tất cả metrics"""
    
    if target_scaler is not None:
        # y_true và y_pred có shape (N, pred_len)
        shape_t = y_true.shape
        shape_p = y_pred.shape
        
        y_true = target_scaler.inverse_transform(y_true.reshape(-1, 1)).reshape(shape_t)
        y_pred = target_scaler.inverse_transform(y_pred.reshape(-1, 1)).reshape(shape_p)
        
    y_pred = np.clip(y_pred, a_min=0, a_max=None)
    
    metrics = {
        "overall": compute_metrics(y_true, y_pred),
        "horizon": compute_horizon_metrics(y_true, y_pred, pred_len),
        "events": compute_event_metrics(y_true, y_pred, threshold=5.0)
    }
    
    return metrics

def compare_experiments(results_dir: str) -> pd.DataFrame:
    """So sánh kết quả các experiment"""
    res_path = Path(results_dir)
    data = []
    
    for exp_dir in sorted(res_path.glob("EXP-*")):
        metrics_file = exp_dir / "metrics.json"
        if metrics_file.exists():
            with open(metrics_file, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
                
            row = {
                "Experiment": exp_dir.name,
                "MAE": metrics["overall"]["MAE"],
                "RMSE": metrics["overall"]["RMSE"],
                "R2": metrics["overall"]["R2"],
                "CC": metrics["overall"]["CC"],
                "CSI (5mm)": metrics["events"]["CSI"]
            }
            # Thêm các mốc t+1, t+24
            if "t+1" in metrics["horizon"]:
                row["MAE t+1"] = metrics["horizon"]["t+1"]["MAE"]
            if "t+24" in metrics["horizon"]:
                row["MAE t+24"] = metrics["horizon"]["t+24"]["MAE"]
                
            data.append(row)
            
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.set_index("Experiment")
        print("\n=== KẾT QUẢ SO SÁNH CÁC EXPERIMENTS ===")
        print(df.to_markdown())
        
    return df
