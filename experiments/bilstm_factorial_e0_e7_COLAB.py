# Auto-generated tu bilstm_factorial_e0_e7_COLAB.ipynb de chay tren Colab hoac local (co GPU).
# Moi cell code duoc tach bang dong "# %% ---- cell ----".
# Chay truc tiep: python bilstm_factorial_e0_e7_COLAB.py

# %% ---- cell ----
# ===== BẢN COLAB — Google Colab với GPU T4 =====
# Thư viện cần có: torch, numpy, pandas, matplotlib, scikit-learn.
import os, sys, json, time, math, warnings, copy
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# `display` hoạt động trong Jupyter; trong CLI Python thường, cần shim
try:
    from IPython.display import display  # noqa: F401
except ImportError:
    def display(x):
        """Shim cho IPython.display.display: in DataFrame/Series ra stdout khi chạy CLI."""
        print(x)

# Matplotlib không mở cửa sổ khi chạy headless
plt.switch_backend("Agg" if not os.environ.get("MPLBACKEND") else None)

assert os.path.exists("/content"), "Bản này chỉ chạy trên Colab. Hãy dùng bản LOCAL."
from google.colab import drive  # type: ignore
drive.mount("/content/drive", force_remount=False)

# Đặt repo ở /content/drive/MyDrive/pbl6. Đổi nếu bạn lưu khác.
DRIVE_ROOT = Path("/content/drive/MyDrive/pbl6")
if not DRIVE_ROOT.exists():
    DRIVE_ROOT = Path("/content/drive/MyDrive/PBL6_v2")
if not DRIVE_ROOT.exists():
    DRIVE_ROOT = Path("/content/drive/MyDrive/PBL6")
if not DRIVE_ROOT.exists():
    raise FileNotFoundError(
        f"Không thấy repo ở {DRIVE_ROOT}. Hãy đặt code và parquet vào MyDrive/pbl6 rồi chạy lại."
    )
ROOT = DRIVE_ROOT
sys.path.insert(0, str(ROOT))
print("[Colab] ROOT =", ROOT)

RESULTS = ROOT / "experiments" / "results"
MODELS  = ROOT / "models"
RESULTS.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", DEVICE)
if DEVICE.type == "cuda":
    print("GPU:", torch.cuda.get_device_name(0))
    torch.backends.cudnn.benchmark = True
    torch.cuda.empty_cache()
else:
    raise RuntimeError("Cần bật GPU: Runtime → Change runtime type → GPU (T4).")

torch.set_num_threads(2)

# Tham số chạy đầy đủ cho Colab (T4 nhanh, ước tính ~20 phút).
BATCH_SIZE  = 256
HIDDEN_DIM  = 64
EPOCHS      = 20
PATIENCE    = 4
SEEDS       = [42, 43, 44]
print(f"Chế độ FULL — {len(SEEDS)} seed × {EPOCHS} epoch × patience {PATIENCE} × batch {BATCH_SIZE}")


# %% ---- cell ----
PARQUET = ROOT / "data" / "danang_full_features_2015_2026.parquet"
df = pd.read_parquet(PARQUET)
print("Shape:", df.shape, "Columns:", list(df.columns))

# Đổi datetime từ giờ VN (+07:00) sang UTC để khớp quy ước CLAUDE.md
df["datetime_local"] = pd.to_datetime(df["datetime"])
df["datetime_utc"]   = df["datetime_local"].dt.tz_convert("UTC")
df = df.dropna(subset=["datetime_utc"]).sort_values("datetime_utc").reset_index(drop=True)

# Bỏ oni_anom theo yêu cầu
if "oni_anom" in df.columns:
    df = df.drop(columns=["oni_anom"])

# Kiểm tra liên tục thời gian: mỗi bước đúng 1 giờ
dt = df["datetime_utc"].diff().dt.total_seconds().dropna()
assert (dt == 3600).all(), "Trục thời gian không liên tục từng giờ"
print("Thời gian UTC:", df["datetime_utc"].min(), "→", df["datetime_utc"].max(),
      "— số giờ:", len(df))
df.head(3)



# %% ---- cell ----
month_local = df["datetime_local"].dt.month
df["season"] = np.where(month_local.isin([5,6,7,8,9,10]), "summer",
                  np.where(month_local.isin([11,12,1,2]), "winter", "spring"))
df["year_local"]  = df["datetime_local"].dt.year
df["month_local"] = month_local

audit = df.groupby("season").agg(
    n_obs=("precipitation", "size"),
    sum_rain=("precipitation", "sum"),
    mean_rain=("precipitation", "mean"),
    pct_zero=("precipitation", lambda s: float((s <= 0.01).mean())),
    pct_heavy=("precipitation", lambda s: float((s >= 10).mean())),
).round(3)
print("=== Phân phối mưa theo mùa (giờ VN) ===")
display(audit)

year_sum = df.groupby("year_local")["precipitation"].agg(["sum", "mean", "size"]).round(3)
print("\n=== Tổng lượng mưa theo năm (giờ VN) ===")
display(year_sum)

# Số giờ mưa theo từng năm
year_events = df.assign(is_rain=lambda x: (x["precipitation"] >= 0.1).astype(int)) \
                .groupby("year_local")["is_rain"].agg(["sum", "mean"]).round(3)
print("\n=== Số giờ có mưa (precipitation >= 0.1 mm) theo năm ===")
display(year_events)



# %% ---- cell ----
# B — baseline: T, R, WS, RH, P, ΔT, ΔR, ΔWS, ΔRH, ΔP, Month
#    T = temperature_2m, R = precipitation, WS = wind_speed_10m,
#    RH = relative_humidity_2m, P = surface_pressure, Month = month_local (1..12)
RAW_BASE = ["temperature_2m", "precipitation", "wind_speed_10m",
            "relative_humidity_2m", "surface_pressure"]
DELTA_BASE = ["d_temperature_2m", "d_precipitation", "d_wind_speed_10m",
              "d_relative_humidity_2m", "d_surface_pressure"]
MONTH_FEATURE = ["month_local"]

# A — Atmospheric Conditions
ATMOSPHERIC = ["cape", "cin", "tcwv", "specific_humidity_850", "swvl1"]
# M — Monsoon Circulation (gió tầng thấp)
MONSOON = ["u_850", "v_850"]
# C — Ocean–Climate Conditions (bỏ oni_anom theo yêu cầu)
OCEAN_CLIMATE = ["sea_surface_temperature"]

# Định nghĩa thí nghiệm theo factorial
EXPERIMENTS = {
    "E0": ["B"],
    "E1": ["B", "A"],
    "E2": ["B", "M"],
    "E3": ["B", "C"],
    "E4": ["B", "A", "M"],
    "E5": ["B", "A", "C"],
    "E6": ["B", "M", "C"],
    "E7": ["B", "A", "M", "C"],
}

GROUP_FEATURES = {
    "B": RAW_BASE + DELTA_BASE + MONTH_FEATURE,
    "A": ATMOSPHERIC,
    "M": MONSOON,
    "C": OCEAN_CLIMATE,
}

def feature_for(experiment_id: str) -> list[str]:
    feats = []
    for g in EXPERIMENTS[experiment_id]:
        feats += GROUP_FEATURES[g]
    return feats

for eid in EXPERIMENTS:
    print(f"{eid} ({'+'.join(EXPERIMENTS[eid])}) — {len(feature_for(eid))} feature:", feature_for(eid))



# %% ---- cell ----
df_feat = df.copy()
for col in RAW_BASE:
    df_feat[f"d_{col}"] = df_feat[col].diff().fillna(0.0)

# Tách train/val/test theo giờ VN để khớp mùa, nhưng tính cửa sổ theo UTC
TRAIN_YEARS = list(range(2015, 2022))   # 2015..2021
VAL_YEAR    = 2022
TEST_YEAR   = 2023
train_mask = df_feat["year_local"].isin(TRAIN_YEARS)
val_mask   = df_feat["year_local"] == VAL_YEAR
test_mask  = df_feat["year_local"] == TEST_YEAR
print("Số giờ mỗi tập:",
      "train", int(train_mask.sum()),
      "val",   int(val_mask.sum()),
      "test",  int(test_mask.sum()))

# Đặc trưng theo thời gian: dùng giờ UTC để khớp target
df_feat["hour_utc"] = df_feat["datetime_utc"].dt.hour
df_feat["doy_utc"]  = df_feat["datetime_utc"].dt.dayofyear
df_feat["sin_hour"] = np.sin(2 * np.pi * df_feat["hour_utc"] / 24)
df_feat["cos_hour"] = np.cos(2 * np.pi * df_feat["hour_utc"] / 24)
df_feat["sin_doy"]  = np.sin(2 * np.pi * df_feat["doy_utc"] / 365.25)
df_feat["cos_doy"]  = np.cos(2 * np.pi * df_feat["doy_utc"] / 365.25)



# %% ---- cell ----
WINDOW = 24
HORIZON = 6
TARGET_COL = "precipitation"

def build_windows(frame: pd.DataFrame, features: list[str], split_name: str):
    """Trả về X (N, 24, F), y (N, 6), meta (DataFrame với datetime_utc, season)."""
    cols = features + ["sin_hour", "cos_hour", "sin_doy", "cos_doy"]
    arr = frame[cols].to_numpy(dtype=np.float32)
    rain = frame[TARGET_COL].to_numpy(dtype=np.float32)
    dt   = frame["datetime_utc"].to_numpy()
    season = frame["season"].to_numpy()
    year_local = frame["year_local"].to_numpy()

    n = len(frame)
    Xs, Ys, metas = [], [], []
    # Bỏ 23 giờ đầu vì thiếu lịch sử 24h; bỏ 6 giờ cuối vì thiếu nhãn t+6
    for t in range(WINDOW - 1, n - HORIZON):
        lo = t - WINDOW + 1              # 24 giờ quá khứ: t-23..t
        hi = t + HORIZON                 # nhãn t+1..t+6
        # Rò rỉ năm: nếu 6 giờ đích vượt ranh giới năm train/val/test → bỏ
        if year_local[t] != year_local[hi]:
            continue
        win_X = arr[lo:lo + WINDOW]      # (24, F)
        win_y = rain[t + 1:hi + 1]       # (6,)
        if (not np.isfinite(win_X).all()) or (not np.isfinite(win_y).all()):
            continue
        Xs.append(win_X)
        Ys.append(win_y)
        metas.append({
            "issue_utc": pd.Timestamp(dt[t]),
            "issue_local": pd.Timestamp(frame["datetime_local"].iloc[t]),
            "season": season[t],
            "year_local": int(year_local[t]),
            "month_local": int(frame["month_local"].iloc[t]),
        })
    X = np.stack(Xs).astype(np.float32)
    y = np.stack(Ys).astype(np.float32)
    meta = pd.DataFrame(metas)
    print(f"[{split_name}] N={len(y)}  X={X.shape}  y={y.shape}  y_mean={y.mean():.3f}  y_sum6_mean={(y.sum(1)).mean():.3f}")
    return X, y, meta

# Chia frame trước khi tạo cửa sổ để chống rò rỉ năm
df_train = df_feat[train_mask].reset_index(drop=True)
df_val   = df_feat[val_mask].reset_index(drop=True)
df_test  = df_feat[test_mask].reset_index(drop=True)

# Vẫn xây cho cả 3 tập với cùng danh sách feature (đã chọn theo E0–E7),
# nhưng trước hết tạo "khung" từ E0 để biết số mẫu; các cấu hình khác
# chỉ khác số feature nên kích thước cửa sổ giống nhau.
Xs = {}
for split_name, frame in [("train", df_train), ("val", df_val), ("test", df_test)]:
    Xs[split_name] = build_windows(frame, feature_for("E7"), split_name)



# %% ---- cell ----
def fit_minmax(X_train_full: np.ndarray, n_feat_base: int) -> dict:
    """Tính min/max cho `n_feat_base` cột đầu của X_train_full.

    Các cột `sin_hour/cos_hour/sin_doy/cos_doy` đã nằm trong [-1, 1] và không
    cần scale; ta chỉ scale đúng `n_feat_base` cột vật lý đầu tiên.
    """
    cols = X_train_full[..., :n_feat_base]
    flat = cols.reshape(-1, n_feat_base)
    finite = np.isfinite(flat).all(axis=1)
    flat = flat[finite]
    mn = flat.min(axis=0)
    mx = flat.max(axis=0)
    rng = np.where(mx - mn < 1e-9, 1.0, mx - mn)
    return {"min": mn.astype(np.float32), "range": rng.astype(np.float32)}

def apply_scale(x: np.ndarray, sc: dict, n_feat_base: int) -> np.ndarray:
    out = x.copy()
    out[..., :n_feat_base] = (out[..., :n_feat_base] - sc["min"]) / sc["range"]
    return out

N_FEAT_E7 = len(feature_for("E7"))
print("Số feature của E7 (kèm time features):", N_FEAT_E7 + 4)



# %% ---- cell ----
class BiLSTMForecaster(nn.Module):
    """Bi-LSTM 24h → 6 lượng mưa giờ.

    BiLSTM chỉ đọc quá khứ, không nhận giờ đích (giống src/bilstm_v2.py
    và src/bilstm_model.py). Đầu ra Softplus để mm luôn không âm.
    """

    def __init__(self, input_dim: int, hidden_dim: int = 64,
                 num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 6),       # 6 giờ tới
            nn.Softplus(),
        )

    def forward(self, x):
        _, (hidden, _) = self.lstm(x)
        context = torch.cat((hidden[-2], hidden[-1]), dim=-1)
        return self.head(context)


class WindowDS(Dataset):
    def __init__(self, X, y):
        self.X, self.y = X, y
    def __len__(self):
        return len(self.X)
    def __getitem__(self, i):
        return torch.from_numpy(self.X[i]), torch.from_numpy(self.y[i])



# %% ---- cell ----
def predict_amount(model, loader, device):
    """Trả về y_true và y_pred đã đảo ngược sqrt → mm."""
    model.eval()
    ys, ps = [], []
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device)
            pred = model(xb).cpu().numpy()   # đã Softplus → mm
            ps.append(pred)
            ys.append(yb.numpy())
    return np.concatenate(ys), np.concatenate(ps)


def train_one(experiment_id: str,
              X_train: np.ndarray, y_train: np.ndarray,
              X_val:   np.ndarray, y_val:   np.ndarray,
              *, seed: int, max_epochs: int = 25, patience: int = 5,
              batch_size: int = 256, lr: float = 1e-3, hidden_dim: int = 64,
              verbose: bool = True):
    torch.manual_seed(seed); np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = DEVICE
    in_dim = X_train.shape[-1]
    model = BiLSTMForecaster(input_dim=in_dim, hidden_dim=hidden_dim).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", factor=0.5, patience=2)

    # Biến đổi sqrt cho nhãn
    y_train_sqrt = np.sqrt(np.maximum(y_train, 0)).astype(np.float32)
    y_val_sqrt   = np.sqrt(np.maximum(y_val, 0)).astype(np.float32)
    train_loader = DataLoader(WindowDS(X_train, y_train_sqrt), batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(WindowDS(X_val, y_val_sqrt), batch_size=batch_size, shuffle=False)

    best_val, best_epoch, best_state = float("inf"), 0, None
    history = []
    bad = 0
    for epoch in range(1, max_epochs + 1):
        model.train()
        losses = []
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad(set_to_none=True)
            pred = model(xb)
            loss = torch.mean((pred - yb) ** 2)   # MSE trên sqrt(y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()
            losses.append(float(loss.detach()))
        train_mse = float(np.mean(losses))

        # Validation: RMSE trên mm gốc (đảo ngược sqrt)
        y_true_mm, y_pred_mm = predict_amount(model, val_loader, device)
        val_rmse_6h = float(np.sqrt(np.mean((y_pred_mm - y_true_mm) ** 2)))
        sched.step(val_rmse_6h)
        history.append({"epoch": epoch, "train_mse_sqrt": train_mse,
                        "val_rmse_total6": val_rmse_6h})
        if verbose:
            print(f"  [{experiment_id} seed{seed}] ep{epoch:02d}  trainMSE_sqrt={train_mse:.4f}  valRMSE_0-6h={val_rmse_6h:.3f} mm")
        if val_rmse_6h < best_val - 1e-6:
            best_val, best_epoch = val_rmse_6h, epoch
            best_state = copy.deepcopy(model.state_dict())
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    return model, history, best_epoch, best_val



# %% ---- cell ----
def persistence_forecast(frame: pd.DataFrame) -> np.ndarray:
    """Trả về mảng (N, 6) dự báo = lượng mưa tại giờ phát hành cho 6 giờ tới.

    Áp dụng trên cùng tập mẫu với mô hình (cùng cửa sổ). Vì frame các tập
    đã được build_windows lấy đúng thứ tự, ta lặp đúng `len(meta)`.
    """
    rain = frame["precipitation"].to_numpy(dtype=np.float32)
    return np.stack([rain] * HORIZON, axis=1)

PERS_TRAIN = persistence_forecast(df_train)
PERS_VAL   = persistence_forecast(df_val)
PERS_TEST  = persistence_forecast(df_test)



# %% ---- cell ----
def totals(y: np.ndarray) -> np.ndarray:
    """Trả về (N, 2) gồm tổng 0–3 h và 0–6 h."""
    return np.stack([y[:, :3].sum(1), y.sum(1)], axis=1)

def rmse_mae(o, f):
    return {"RMSE": float(np.sqrt(np.mean((f - o) ** 2))),
            "MAE":  float(np.mean(np.abs(f - o)))}

def contingency(o, f, thr):
    yo, yf = (o >= thr), (f >= thr)
    hits = int((yo & yf).sum()); miss = int((yo & ~yf).sum()); fa = int((~yo & yf).sum())
    n_pos = hits + miss
    POD = hits / n_pos if n_pos else float("nan")
    FAR = fa / (hits + fa) if (hits + fa) else float("nan")
    CSI = hits / (hits + miss + fa) if (hits + miss + fa) else float("nan")
    return {"POD": POD, "FAR": FAR, "CSI": CSI,
            "hits": hits, "miss": miss, "fa": fa, "n_obs": n_pos}

def evaluate(y_true_mm: np.ndarray, y_pred_mm: np.ndarray) -> dict:
    t_true = totals(y_true_mm); t_pred = totals(y_pred_mm)
    out = {}
    for name, idx in [("total3h", 0), ("total6h", 1)]:
        m = rmse_mae(t_true[:, idx], t_pred[:, idx])
        out[f"RMSE_{name}"] = m["RMSE"]
        out[f"MAE_{name}"]  = m["MAE"]
    out.update({f"CSI_total3h>=10": contingency(t_true[:,0], t_pred[:,0], 10)["CSI"]})
    out.update({f"CSI_total6h>=10": contingency(t_true[:,1], t_pred[:,1], 10)["CSI"]})
    out.update({f"CSI_total6h>=25": contingency(t_true[:,1], t_pred[:,1], 25)["CSI"]})
    out.update({f"POD_total6h>=10": contingency(t_true[:,1], t_pred[:,1], 10)["POD"]})
    out.update({f"FAR_total6h>=10": contingency(t_true[:,1], t_pred[:,1], 10)["FAR"]})
    return out



# %% ---- cell ----
# Dùng tham số đã đặt ở cell env_setup: BATCH_SIZE, EPOCHS, PATIENCE, SEEDS, HIDDEN_DIM
print(f"Chạy: {len(SEEDS)} seed × {EPOCHS} epoch × batch {BATCH_SIZE}, hidden {HIDDEN_DIM}")

results = []          # mỗi dòng = 1 (E, seed) trên 1 split
histories = {}        # lưu learning curve
predictions = {}      # lưu dự báo test cho reliability & event plot

for eid in EXPERIMENTS:
    print(f"\n========== {eid} ({'+'.join(EXPERIMENTS[eid])}) ==========")
    feats = feature_for(eid)
    full_feats_E7 = feature_for("E7") + ["sin_hour", "cos_hour", "sin_doy", "cos_doy"]
    idx = [full_feats_E7.index(f) for f in feats] + \
          [full_feats_E7.index(f) for f in ["sin_hour", "cos_hour", "sin_doy", "cos_doy"]]
    n_feat_base = len(feats)

    X_train = Xs["train"][0][..., idx]
    X_val   = Xs["val"][0][..., idx]
    X_test  = Xs["test"][0][..., idx]
    y_train, y_val, y_test = Xs["train"][1], Xs["val"][1], Xs["test"][1]
    meta_train, meta_val, meta_test = Xs["train"][2], Xs["val"][2], Xs["test"][2]

    sc = fit_minmax(X_train, n_feat_base)
    X_train_s = apply_scale(X_train, sc, n_feat_base)
    X_val_s   = apply_scale(X_val,   sc, n_feat_base)
    X_test_s  = apply_scale(X_test,  sc, n_feat_base)

    histories[eid] = []
    for seed in SEEDS:
        t0 = time.time()
        model, hist, best_ep, best_val = train_one(
            eid, X_train_s, y_train, X_val_s, y_val,
            seed=seed, max_epochs=EPOCHS, patience=PATIENCE,
            batch_size=BATCH_SIZE, hidden_dim=HIDDEN_DIM,
            verbose=(seed == SEEDS[0]))
        elapsed = time.time() - t0

        test_loader = DataLoader(WindowDS(X_test_s, np.sqrt(np.maximum(y_test, 0)).astype(np.float32)),
                                  batch_size=BATCH_SIZE, shuffle=False)
        y_true_mm, y_pred_mm = predict_amount(model, test_loader, DEVICE)
        metrics = evaluate(y_true_mm, y_pred_mm)
        row = {"experiment": eid, "seed": seed,
               "best_epoch": best_ep, "best_val_rmse_0-6": best_val,
               "seconds": round(elapsed, 1), **metrics}
        results.append(row)
        histories[eid].append(hist)
        if seed == SEEDS[0]:
            predictions[eid] = {"y_true": y_true_mm, "y_pred": y_pred_mm,
                                "meta": meta_test.reset_index(drop=True)}
        ckpt_path = MODELS / f"bilstm_{eid}_seed{seed}.pt"
        torch.save({"state_dict": model.state_dict(),
                    "feature_names": feats,
                    "scaler": {"min": sc["min"].tolist(), "range": sc["range"].tolist()},
                    "best_epoch": best_ep, "seed": seed, "experiment": eid},
                   ckpt_path)
        if seed == SEEDS[0]:
            print(f"  -> {eid} seed{seed}: valRMSE0-6={best_val:.3f} mm, "
                  f"testRMSE0-6={metrics['RMSE_total6h']:.3f}, "
                  f"testCSI6h>=10={metrics['CSI_total6h>=10']:.3f}")
    if DEVICE.type == "cuda":
        torch.cuda.empty_cache()

df_res = pd.DataFrame(results)
df_res.to_csv(RESULTS / "bilstm_factorial_e0_e7.csv", index=False)
print("\nBảng kết quả (test 2023):")
display(df_res.round(4))


# %% ---- cell ----
metric_cols = [c for c in df_res.columns if c.startswith(("RMSE_", "MAE_", "CSI_", "POD_", "FAR_"))]
agg = df_res.groupby("experiment")[metric_cols].agg(["mean", "std"]).round(3)
agg.columns = [f"{c}_{stat}" for c, stat in agg.columns]
agg = agg.reset_index()

# Baseline persistence trên cùng test
PERS_TEST_TOTAL = totals(PERS_TEST)
Y_TEST_TOTAL    = totals(Xs["test"][1])
pers_row = {
    "RMSE_total3h_mean":  float(np.sqrt(np.mean((PERS_TEST_TOTAL[:,0]-Y_TEST_TOTAL[:,0])**2))),
    "MAE_total3h_mean":   float(np.mean(np.abs(PERS_TEST_TOTAL[:,0]-Y_TEST_TOTAL[:,0]))),
    "RMSE_total6h_mean":  float(np.sqrt(np.mean((PERS_TEST_TOTAL[:,1]-Y_TEST_TOTAL[:,1])**2))),
    "MAE_total6h_mean":   float(np.mean(np.abs(PERS_TEST_TOTAL[:,1]-Y_TEST_TOTAL[:,1]))),
    "CSI_total3h>=10_mean": contingency(Y_TEST_TOTAL[:,0], PERS_TEST_TOTAL[:,0], 10)["CSI"],
    "CSI_total6h>=10_mean": contingency(Y_TEST_TOTAL[:,1], PERS_TEST_TOTAL[:,1], 10)["CSI"],
    "CSI_total6h>=25_mean": contingency(Y_TEST_TOTAL[:,1], PERS_TEST_TOTAL[:,1], 25)["CSI"],
}
pers_table = pd.DataFrame([{"experiment": "PERS", **pers_row}])
agg_with_pers = pd.concat([pers_table, agg], ignore_index=True)
agg_with_pers.to_csv(RESULTS / "bilstm_factorial_summary.csv", index=False)
print("=== Bảng tổng hợp (mean ± std trên 3 seed; PERS là baseline đơn lẻ) ===")
display(agg_with_pers.round(3))



# %% ---- cell ----
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
fig, axes = plt.subplots(2, 4, figsize=(18, 7), sharex=True)
for ax, eid in zip(axes.ravel(), EXPERIMENTS):
    for h in histories[eid]:
        ep = [e["epoch"] for e in h]
        rmse = [e["val_rmse_total6"] for e in h]
        ax.plot(ep, rmse, lw=1.4, alpha=0.85)
    ax.set_title(f"{eid} ({'+'.join(EXPERIMENTS[eid])})")
    ax.set_xlabel("epoch"); ax.set_ylabel("val RMSE 0–6 h (mm)")
fig.suptitle("Learning curves — val RMSE tổng 0–6 h trên 3 seed", fontsize=14)
fig.tight_layout()
fig.savefig(RESULTS / "bilstm_factorial_curves.png", bbox_inches="tight")
plt.show()



# %% ---- cell ----
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
labels = list(agg_with_pers["experiment"])
x = np.arange(len(labels))

# RMSE tổng 0–3 h
axes[0].bar(x, agg_with_pers["RMSE_total3h_mean"],
            yerr=agg_with_pers.get("RMSE_total3h_std", pd.Series([0]*len(labels))), capsize=3)
axes[0].set_xticks(x); axes[0].set_xticklabels(labels, rotation=0)
axes[0].set_ylabel("RMSE (mm)"); axes[0].set_title("RMSE tổng 0–3 h (test 2023)")

# RMSE tổng 0–6 h
axes[1].bar(x, agg_with_pers["RMSE_total6h_mean"],
            yerr=agg_with_pers.get("RMSE_total6h_std", pd.Series([0]*len(labels))), capsize=3)
axes[1].set_xticks(x); axes[1].set_xticklabels(labels, rotation=0)
axes[1].set_ylabel("RMSE (mm)"); axes[1].set_title("RMSE tổng 0–6 h (test 2023)")

# CSI tổng 6h >= 10
axes[2].bar(x, agg_with_pers["CSI_total6h>=10_mean"],
            yerr=agg_with_pers.get("CSI_total6h>=10_std", pd.Series([0]*len(labels))), capsize=3)
axes[2].set_xticks(x); axes[2].set_xticklabels(labels, rotation=0)
axes[2].set_ylabel("CSI"); axes[2].set_title("CSI tổng 0–6 h ≥ 10 mm (test 2023)")
axes[2].set_ylim(0, max(0.5, float(agg_with_pers["CSI_total6h>=10_mean"].max() * 1.3)))
fig.suptitle("So sánh 8 thí nghiệm + persistence", fontsize=14)
fig.tight_layout()
fig.savefig(RESULTS / "bilstm_factorial_bars.png", bbox_inches="tight")
plt.show()



# %% ---- cell ----
def reliability(prob, event, n_bins=10):
    bins = np.clip((np.asarray(prob) * n_bins).astype(int), 0, n_bins - 1)
    out = []
    for b in range(n_bins):
        m = bins == b
        if m.sum() == 0:
            continue
        out.append({"bin_lo": b/n_bins, "bin_hi": (b+1)/n_bins,
                    "n": int(m.sum()), "mean_prob": float(prob[m].mean()),
                    "obs_freq": float(event[m].mean())})
    return pd.DataFrame(out)

e7_pred = predictions["E7"]
thr = 10
t_pred6 = totals(e7_pred["y_pred"])[:, 1]
t_true6 = totals(e7_pred["y_true"])[:, 1]
event = (t_true6 >= thr).astype(float)
prob = np.clip(t_pred6 / thr, 0, 1)
rel = reliability(prob, event, n_bins=10)
fig, ax = plt.subplots(figsize=(6, 6))
ax.plot([0, 1], [0, 1], "k--", lw=1, label="Hoàn hảo")
ax.bar(rel["bin_lo"], rel["obs_freq"], width=0.1, align="edge",
        alpha=0.6, edgecolor="black", label="E7")
ax.plot(rel["bin_lo"] + 0.05, rel["mean_prob"], "ro-", label="Đường hiệu chỉnh")
ax.set_xlabel("Xác suất dự báo (min(1, y_hat/10))"); ax.set_ylabel("Tần suất quan trắc")
ax.set_title(f"Reliability — E7, tổng 0–6 h ≥ {thr} mm (test 2023)")
ax.set_xlim(0, 1); ax.set_ylim(0, max(0.5, float(rel["obs_freq"].max() * 1.4)))
ax.legend(); fig.tight_layout()
fig.savefig(RESULTS / "bilstm_factorial_reliability.png", bbox_inches="tight")
plt.show()
print(rel.round(3))



# %% ---- cell ----
e7 = predictions["E7"]
totals_true = totals(e7["y_true"])[:, 1]
order = np.argsort(-totals_true)
TOP = 5
fig, axes = plt.subplots(TOP, 1, figsize=(11, 2.3 * TOP), sharex=False)
for ax, idx in zip(axes, order[:TOP]):
    yt = e7["y_true"][idx]
    yp = e7["y_pred"][idx]
    issue = e7["meta"]["issue_local"].iloc[idx]
    hours = np.arange(1, 7)
    ax.bar(hours - 0.18, yt, width=0.36, label="Quan trắc", color="#1f77b4")
    ax.bar(hours + 0.18, yp, width=0.36, label="E7", color="#ff7f0e")
    ax.bar(hours,        yt[0]*np.ones(6), width=0.36, color="#cccccc", alpha=0.5, label="Persistence")
    ax.set_title(f"Phát hành {issue}, tổng 0–6 h = {totals_true[idx]:.1f} mm")
    ax.set_xlabel("Giờ tới (t+1…t+6)"); ax.set_ylabel("mm/h")
    ax.legend(loc="upper right", fontsize=8)
fig.suptitle("5 sự kiện mưa lớn nhất 2023 — E7 vs Quan trắc vs Persistence", fontsize=13)
fig.tight_layout()
fig.savefig(RESULTS / "bilstm_factorial_event.png", bbox_inches="tight")
plt.show()



# %% ---- cell ----
season_rows = []
for eid in EXPERIMENTS:
    pred = predictions[eid]
    tot_true = totals(pred["y_true"])
    tot_pred = totals(pred["y_pred"])
    season = pred["meta"]["season"].values
    for s in ["summer", "winter", "spring"]:
        m = season == s
        if m.sum() == 0:
            continue
        rmse6 = float(np.sqrt(np.mean((tot_pred[m,1]-tot_true[m,1])**2)))
        csi10 = contingency(tot_true[m,1], tot_pred[m,1], 10)["CSI"]
        csi25 = contingency(tot_true[m,1], tot_pred[m,1], 25)["CSI"]
        season_rows.append({"experiment": eid, "season": s, "n": int(m.sum()),
                            "RMSE_0-6": rmse6, "CSI_0-6_>=10": csi10,
                            "CSI_0-6_>=25": csi25})
season_df = pd.DataFrame(season_rows)
season_df.to_csv(RESULTS / "bilstm_factorial_by_season.csv", index=False)
pivot = season_df.pivot_table(index="experiment", columns="season",
                              values="RMSE_0-6").round(3)
print("RMSE 0–6 h theo mùa (test 2023):")
display(pivot)
pivot_csi = season_df.pivot_table(index="experiment", columns="season",
                                  values="CSI_0-6_>=10").round(3)
print("CSI 0–6 h ≥ 10 mm theo mùa (test 2023):")
display(pivot_csi)



# %% ---- cell ----
summary = {
    "data": str(PARQUET.relative_to(ROOT)),
    "splits": {"train": f"{TRAIN_YEARS[0]}–{TRAIN_YEARS[-1]}", "val": VAL_YEAR, "test": TEST_YEAR},
    "window": WINDOW, "horizon": HORIZON,
    "target_transform": "sqrt(y) → MSE → inverse sqrt",
    "experiments": EXPERIMENTS,
    "groups": GROUP_FEATURES,
    "seeds": SEEDS, "epochs": EPOCHS, "patience": PATIENCE,
    "device": str(DEVICE),
    "results_csv": str((RESULTS / "bilstm_factorial_e0_e7.csv").relative_to(ROOT)),
    "summary_csv": str((RESULTS / "bilstm_factorial_summary.csv").relative_to(ROOT)),
    "season_csv": str((RESULTS / "bilstm_factorial_by_season.csv").relative_to(ROOT)),
    "plots": [str((RESULTS / f).relative_to(ROOT)) for f in
              ["bilstm_factorial_curves.png", "bilstm_factorial_bars.png",
               "bilstm_factorial_reliability.png", "bilstm_factorial_event.png"]],
    "checkpoints": [str((MODELS / f"bilstm_E{i}_seed{s}.pt").relative_to(ROOT))
                    for i in range(8) for s in SEEDS],
}
(RESULTS / "bilstm_factorial_run.json").write_text(json.dumps(summary, indent=2, default=str),
                                                  encoding="utf-8")
print("Đã lưu:")
for k in ["results_csv", "summary_csv", "season_csv"] + summary["plots"]:
    print(" -", k)



