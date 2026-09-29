import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from baseline_model import BiLSTM, TimeSeriesDataset, create_sequences, SEQ_LEN, PRED_HORIZON, DEVICE, TARGET_COL, BASELINE_DATASET, CHECKPOINT_PATH

def evaluate():
    df = pd.read_parquet(BASELINE_DATASET)
    if "hour" not in df.columns:
        df["hour"] = df["datetime"].dt.hour
    df = df.sort_values("datetime").reset_index(drop=True)
    
    train_mask = df["datetime"] < pd.Timestamp("2023-01-01", tz=df["datetime"].dt.tz)
    test_mask = df["datetime"] >= pd.Timestamp("2025-01-01", tz=df["datetime"].dt.tz)
    
    exclude_cols = ["datetime", TARGET_COL]
    feature_cols = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    
    df[TARGET_COL] = np.log1p(df[TARGET_COL].clip(lower=0))
    
    train_df = df[train_mask]
    test_df = df[test_mask]
    
    scaler_x = StandardScaler()
    scaler_x.fit(train_df[feature_cols].values)
    
    X_test = scaler_x.transform(test_df[feature_cols].values)
    y_test = test_df[TARGET_COL].values
    
    X_test_seq, y_test_seq = create_sequences(X_test, y_test, SEQ_LEN, PRED_HORIZON)
    
    test_dataset = TimeSeriesDataset(X_test_seq, y_test_seq)
    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=256, shuffle=False)
    
    input_dim = len(feature_cols)
    model = BiLSTM(input_dim=input_dim, hidden_dim=128, num_layers=2, output_dim=PRED_HORIZON).to(DEVICE)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=DEVICE))
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
    
    preds_inv = np.expm1(preds).clip(min=0)
    actuals_inv = np.expm1(actuals).clip(min=0)
    
    mae = mean_absolute_error(actuals_inv, preds_inv)
    rmse = np.sqrt(mean_squared_error(actuals_inv, preds_inv))
    r2 = r2_score(actuals_inv, preds_inv)
    
    print(f"MAE: {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R2: {r2:.4f}")

if __name__ == "__main__":
    evaluate()
