# ==============================================================================
# baseline_model.py — Huấn luyện Mô hình Đối chứng Bi-LSTM
# ==============================================================================
"""
Module 4: Huấn luyện Baseline Model bằng PyTorch.

Sử dụng tập dữ liệu dataset_baseline_2015_2026.parquet
- Train: 2015-01-01 -> 2022-12-31
- Val:   2023-01-01 -> 2024-12-31
- Test:  2025-01-01 -> 2026-08-31

Mô hình: Bi-LSTM dự đoán precipitation từ t+1 đến t+6.

Sử dụng:
  python baseline_model.py
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import copy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
BASELINE_DATASET = DATASETS_DIR / "dataset_baseline_2015_2026.parquet"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_PATH = CHECKPOINT_DIR / "baseline_bilstm.pt"

# --- Cấu hình mô hình ---
SEQ_LEN = 48         # Nhìn lại 48 giờ
PRED_HORIZON = 6     # Dự báo 6 giờ tới
BATCH_SIZE = 256
EPOCHS = 50
PATIENCE = 10
LR = 1e-3
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

TARGET_COL = "precipitation"

class TimeSeriesDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def create_sequences(X, y, seq_len, pred_horizon):
    """
    Tạo các sequence: (seq_len, n_features) -> (pred_horizon, 1)
    """
    Xs, ys = [], []
    for i in range(len(X) - seq_len - pred_horizon + 1):
        Xs.append(X[i:(i + seq_len)])
        ys.append(y[(i + seq_len):(i + seq_len + pred_horizon)])
    return np.array(Xs), np.array(ys)


class BiLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, output_dim, dropout=0.3):
        super(BiLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )
        # Bidirectional nên out dimension là hidden_dim * 2
        self.fc1 = nn.Linear(hidden_dim * 2, 128)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        self.fc2 = nn.Linear(128, output_dim)

    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        out, _ = self.lstm(x)
        # Lấy timestep cuối cùng
        out = out[:, -1, :] 
        out = self.fc1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        return out


def train_model():
    logger.info("=" * 70)
    logger.info("TRAINING BASELINE Bi-LSTM (Module 4)")
    logger.info("=" * 70)
    logger.info("Device: %s", DEVICE)

    if not BASELINE_DATASET.exists():
        logger.error("Dataset not found: %s", BASELINE_DATASET)
        sys.exit(1)

    df = pd.read_parquet(BASELINE_DATASET)
    
    # Tạo biến thời gian (giờ) thủ công cho Baseline nếu chưa có
    if "hour" not in df.columns:
        df["hour"] = df["datetime"].dt.hour
    
    # Sắp xếp theo datetime
    df = df.sort_values("datetime").reset_index(drop=True)
    
    # Tách dữ liệu Train/Val/Test
    # Train: 2015-01-01 -> 2022-12-31
    # Val:   2023-01-01 -> 2024-12-31
    # Test:  2025-01-01 -> end
    train_mask = df["datetime"] < pd.Timestamp("2023-01-01", tz=df["datetime"].dt.tz)
    val_mask = (df["datetime"] >= pd.Timestamp("2023-01-01", tz=df["datetime"].dt.tz)) & (df["datetime"] < pd.Timestamp("2025-01-01", tz=df["datetime"].dt.tz))
    test_mask = df["datetime"] >= pd.Timestamp("2025-01-01", tz=df["datetime"].dt.tz)

    # Nếu DataFrame không có đủ features, chọn những column số làm input
    exclude_cols = ["datetime", TARGET_COL]
    feature_cols = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    logger.info("Features used (%d): %s", len(feature_cols), feature_cols)

    # Chuyển đổi target sang log scale (log1p)
    df[TARGET_COL] = np.log1p(df[TARGET_COL].clip(lower=0)) # Tránh < 0

    train_df = df[train_mask]
    val_df = df[val_mask]
    test_df = df[test_mask]

    logger.info("Data splits: Train=%d, Val=%d, Test=%d", len(train_df), len(val_df), len(test_df))

    scaler_x = StandardScaler()
    
    X_train = scaler_x.fit_transform(train_df[feature_cols].values)
    y_train = train_df[TARGET_COL].values
    
    X_val = scaler_x.transform(val_df[feature_cols].values)
    y_val = val_df[TARGET_COL].values
    
    X_test = scaler_x.transform(test_df[feature_cols].values)
    y_test = test_df[TARGET_COL].values

    # Tạo sequence
    logger.info("Creating sequences (SEQ_LEN=%d, PRED_HORIZON=%d)...", SEQ_LEN, PRED_HORIZON)
    X_train_seq, y_train_seq = create_sequences(X_train, y_train, SEQ_LEN, PRED_HORIZON)
    X_val_seq, y_val_seq = create_sequences(X_val, y_val, SEQ_LEN, PRED_HORIZON)
    X_test_seq, y_test_seq = create_sequences(X_test, y_test, SEQ_LEN, PRED_HORIZON)

    # DataLoaders
    train_dataset = TimeSeriesDataset(X_train_seq, y_train_seq)
    val_dataset = TimeSeriesDataset(X_val_seq, y_val_seq)
    test_dataset = TimeSeriesDataset(X_test_seq, y_test_seq)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # Model Init
    input_dim = len(feature_cols)
    model = BiLSTM(input_dim=input_dim, hidden_dim=128, num_layers=2, output_dim=PRED_HORIZON).to(DEVICE)
    
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    # Training Loop
    logger.info("Starting training...")
    best_val_loss = float('inf')
    best_model_weights = copy.deepcopy(model.state_dict())
    patience_counter = 0

    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * batch_x.size(0)
            
        train_loss /= len(train_loader.dataset)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item() * batch_x.size(0)
        val_loss /= len(val_loader.dataset)

        logger.info("Epoch [%2d/%2d] | Train Loss: %.4f | Val Loss: %.4f", epoch+1, EPOCHS, train_loss, val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_weights = copy.deepcopy(model.state_dict())
            patience_counter = 0
            torch.save(model.state_dict(), CHECKPOINT_PATH)
            logger.info("  -> Saved new best model")
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                logger.info("Early stopping triggered at epoch %d", epoch+1)
                break

    # Evaluation on Test Set
    logger.info("Evaluating on Test Set...")
    model.load_state_dict(best_model_weights)
    model.eval()
    
    preds, actuals = [], []
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            batch_x = batch_x.to(DEVICE)
            outputs = model(batch_x)
            preds.append(outputs.cpu().numpy())
            actuals.append(batch_y.numpy())
            
    preds = np.concatenate(preds, axis=0)
    actuals = np.concatenate(actuals, axis=0)

    # Back-transform từ log1p (expm1)
    preds_inv = np.expm1(preds).clip(min=0)
    actuals_inv = np.expm1(actuals).clip(min=0)

    # Tính metrics trung bình qua 6 horizons
    mae = mean_absolute_error(actuals_inv, preds_inv)
    rmse = np.sqrt(mean_squared_error(actuals_inv, preds_inv))
    r2 = r2_score(actuals_inv, preds_inv)

    logger.info("=" * 50)
    logger.info("TEST METRICS (Baseline Benchmark)")
    logger.info("  MAE:  %.4f mm/h", mae)
    logger.info("  RMSE: %.4f mm/h", rmse)
    logger.info("  R2:   %.4f", r2)
    logger.info("=" * 50)

    # Trả về metrics để module orchestrator in ra
    return {"mae": mae, "rmse": rmse, "r2": r2}

if __name__ == "__main__":
    train_model()
