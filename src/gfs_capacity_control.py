"""GRU controls with fixed training budget and explicit redundant raw inputs."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from src.gfs_daily import RAW_MET, TERRAIN
from src.gfs_daily_gru import DailyGRU, arrays, normalizers, tensors, loss_function, predict

PROJECTION_SEED = 20261117
PROJECTION_NAMES = RAW_MET + TERRAIN


def fixed_projection():
    matrix = np.random.default_rng(PROJECTION_SEED).normal(size=(6, len(PROJECTION_NAMES)))
    return (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).astype("float32")


def control_arrays(frame, config, train=None, projection=None):
    if config not in ("GRU_N3_LINEAR6", "GRU_N3_WIDE"):
        raise ValueError("Unknown capacity control")
    raw = arrays(frame, "N3")
    if config == "GRU_N3_LINEAR6":
        index = [raw["names"].index(n) for n in PROJECTION_NAMES]
        inputs = raw["context"][:, :, index]
        if projection is None:
            if train is None or not np.asarray(train).any():
                raise ValueError("Fit projection scaling on training rows only")
            projection = dict(mean=inputs[train].mean((0, 1)),
                std=np.maximum(inputs[train].std((0, 1)), 1e-5), matrix=fixed_projection())
        extra = ((inputs-projection["mean"])/projection["std"]) @ projection["matrix"].T
        raw["context"] = np.concatenate([raw["context"], extra], axis=2).astype("float32")
        raw["names"] += [f"raw_linear_{j+1}" for j in range(6)]
    return raw, projection


def fit_control(frame, config, train, candidate, epochs, seed, callback=None):
    if frame.target_end_utc.dt.tz_convert("Asia/Ho_Chi_Minh").dt.year.max() > 2024:
        raise ValueError("Control fitting cannot read holdout targets")
    raw, projection = control_arrays(frame, config, train)
    norm = normalizers(raw, train)
    inputs = tensors(raw, norm)
    torch.set_num_threads(4)
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True, warn_only=True)
    model = DailyGRU(len(raw["names"]), candidate["hidden"], candidate["head"]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=candidate["lr"], weight_decay=.001)
    loader = DataLoader(TensorDataset(*[v[train] for v in inputs]), batch_size=256,
        shuffle=True, generator=torch.Generator().manual_seed(seed), num_workers=0)
    curves = []
    for epoch in range(1, epochs+1):
        model.train()
        total = 0.
        seen = 0
        for batch in loader:
            h, c, s, y, e = [v.to(device) for v in batch]
            optimizer.zero_grad(set_to_none=True)
            point, logits = model(h, c, s)
            loss = loss_function(point, logits, y, e)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite control loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            total += float(loss.detach().cpu())*len(h)
            seen += len(h)
        row = dict(epoch=epoch, train_loss=total/seen)
        curves.append(row)
        if callback:
            callback(row)
    artifact = dict(state={k: v.detach().cpu() for k, v in model.state_dict().items()},
        config=config, normalizers=norm, projection=projection, candidate=candidate,
        seed=seed, epochs=epochs, features=raw["names"], curves=curves,
        parameter_count=sum(v.numel() for v in model.parameters()), device=str(device),
        training_rows=int(np.asarray(train).sum()), early_stopping=False)
    output = predict(model, inputs, norm["target_scale"], device)
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return artifact, output


def replay_control(frame, artifact, cpu=False):
    raw, _ = control_arrays(frame, artifact["config"], projection=artifact["projection"])
    if raw["names"] != artifact["features"]:
        raise ValueError("Control feature order changed")
    inputs = tensors(raw, artifact["normalizers"])
    device = torch.device("cpu" if cpu or not torch.cuda.is_available() else "cuda")
    c = artifact["candidate"]
    model = DailyGRU(len(raw["names"]), c["hidden"], c["head"]).to(device)
    model.load_state_dict(artifact["state"])
    result = predict(model, inputs, artifact["normalizers"]["target_scale"], device)
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return result
