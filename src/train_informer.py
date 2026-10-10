import os
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

@dataclass
class InformerTrainingConfig:
    learning_rate: float
    weight_decay: float
    max_epochs: int
    patience: int
    device: str
    save_dir: str
    experiment_name: str

@dataclass
class TrainingResult:
    model: nn.Module
    history: Dict[str, list]
    best_epoch: int
    best_val_loss: float
    y_true_test: np.ndarray
    y_pred_test: np.ndarray

def train_informer(
    train_loader,
    val_loader,
    test_loader,
    model: nn.Module,
    config: InformerTrainingConfig,
    feature_cols: list
) -> TrainingResult:
    
    os.makedirs(config.save_dir, exist_ok=True)
    device = torch.device(config.device)
    model = model.to(device)
    
    criterion = nn.MSELoss()
    optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    scheduler = CosineAnnealingWarmRestarts(optimizer, T_0=10, eta_min=1e-6)
    
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    
    history = {'train_loss': [], 'val_loss': []}
    
    model_save_path = os.path.join(config.save_dir, f"{config.experiment_name}.pth")
    
    logger.info(f"Bắt đầu huấn luyện mô hình: {config.experiment_name}")
    
    for epoch in range(config.max_epochs):
        model.train()
        train_losses = []
        
        for batch_idx, (x_enc, x_mark_enc, x_dec, x_mark_dec, y) in enumerate(train_loader):
            x_enc = x_enc.to(device)
            x_mark_enc = x_mark_enc.to(device)
            x_dec = x_dec.to(device)
            x_mark_dec = x_mark_dec.to(device)
            y = y.to(device)
            
            optimizer.zero_grad()
            
            # Forward pass
            # Informer output có thể là (B, pred_len, d_out) hoặc tương tự. Cần bóp lại (B, pred_len)
            preds = model(x_enc, x_mark_enc, x_dec, x_mark_dec)
            if preds.shape[-1] == 1:
                preds = preds.squeeze(-1)
                
            loss = criterion(preds, y)
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            train_losses.append(loss.item())
            
        scheduler.step()
        
        # Validation
        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch_idx, (x_enc, x_mark_enc, x_dec, x_mark_dec, y) in enumerate(val_loader):
                x_enc = x_enc.to(device)
                x_mark_enc = x_mark_enc.to(device)
                x_dec = x_dec.to(device)
                x_mark_dec = x_mark_dec.to(device)
                y = y.to(device)
                
                preds = model(x_enc, x_mark_enc, x_dec, x_mark_dec)
                if preds.shape[-1] == 1:
                    preds = preds.squeeze(-1)
                loss = criterion(preds, y)
                val_losses.append(loss.item())
                
        avg_train_loss = np.mean(train_losses)
        avg_val_loss = np.mean(val_losses)
        
        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(avg_val_loss)
        
        logger.info(f"Epoch {epoch+1}/{config.max_epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
        
        # Early stopping & Save best model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            patience_counter = 0
            
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'feature_cols': feature_cols,
                'val_loss': best_val_loss
            }, model_save_path)
            logger.info(f"  -> Lưu model mới tốt nhất tại epoch {epoch+1}")
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                logger.info(f"Early stopping kích hoạt tại epoch {epoch+1}")
                break
                
    # Load best model for prediction
    logger.info("Tải mô hình tốt nhất để dự đoán trên test set...")
    checkpoint = torch.load(model_save_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    y_true_test, y_pred_test = predict_informer(model, test_loader, device)
    
    return TrainingResult(
        model=model,
        history=history,
        best_epoch=best_epoch,
        best_val_loss=best_val_loss,
        y_true_test=y_true_test,
        y_pred_test=y_pred_test
    )

def predict_informer(model: nn.Module, data_loader, device: torch.device) -> Tuple[np.ndarray, np.ndarray]:
    model.eval()
    y_trues = []
    y_preds = []
    
    with torch.no_grad():
        for x_enc, x_mark_enc, x_dec, x_mark_dec, y in data_loader:
            x_enc = x_enc.to(device)
            x_mark_enc = x_mark_enc.to(device)
            x_dec = x_dec.to(device)
            x_mark_dec = x_mark_dec.to(device)
            
            preds = model(x_enc, x_mark_enc, x_dec, x_mark_dec)
            if preds.shape[-1] == 1:
                preds = preds.squeeze(-1)
                
            y_trues.append(y.cpu().numpy())
            y_preds.append(preds.cpu().numpy())
            
    y_true_all = np.concatenate(y_trues, axis=0)
    y_pred_all = np.concatenate(y_preds, axis=0)
    
    # Clip predictions (precipitation >= 0)
    y_pred_all = np.clip(y_pred_all, a_min=0, a_max=None)
    
    return y_true_all, y_pred_all
