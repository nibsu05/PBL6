from dataclasses import dataclass
from typing import List

@dataclass
class ExperimentConfig:
    name: str
    description: str
    feature_cols: List[str]
    # Informer architecture
    seq_len: int = 168
    label_len: int = 48
    pred_len: int = 24
    d_model: int = 128
    n_heads: int = 8
    e_layers: int = 2
    d_layers: int = 1
    d_ff: int = 256
    factor: int = 5
    dropout: float = 0.1
    activation: str = 'gelu'
    distil: bool = True
    # Training
    batch_size: int = 32
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    max_epochs: int = 50
    patience: int = 10
    seed: int = 42

EXPERIMENTS = {
    "EXP-0_surface": ExperimentConfig(
        name="EXP-0_surface",
        description="Baseline: chỉ dữ liệu bề mặt Open-Meteo",
        feature_cols=[
            "temperature_2m", "relative_humidity_2m", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "precipitation",
        ],
    ),
    "EXP-1_sst": ExperimentConfig(
        name="EXP-1_sst",
        description="Baseline + SST biển",
        feature_cols=[
            "temperature_2m", "relative_humidity_2m", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "precipitation",
            "sea_surface_temperature",
        ],
    ),
    "EXP-2_thermo": ExperimentConfig(
        name="EXP-2_thermo",
        description="+ Nhiệt động (CAPE, TCWV, CIN)",
        feature_cols=[
            "temperature_2m", "relative_humidity_2m", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "precipitation",
            "sea_surface_temperature",
            "cape", "tcwv", "cin",  # cin will be expanded to cin_value + is_convective
        ],
    ),
    "EXP-3_soil": ExperimentConfig(
        name="EXP-3_soil",
        description="+ Độ ẩm đất",
        feature_cols=[
            "temperature_2m", "relative_humidity_2m", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "precipitation",
            "sea_surface_temperature",
            "cape", "tcwv", "cin",
            "swvl1",
        ],
    ),
    "EXP-4_full": ExperimentConfig(
        name="EXP-4_full",
        description="Full: + Gió & ẩm 850 hPa",
        feature_cols=[
            "temperature_2m", "relative_humidity_2m", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "precipitation",
            "sea_surface_temperature",
            "cape", "tcwv", "cin",
            "swvl1",
            "u_850", "v_850", "specific_humidity_850",
        ],
    ),
}

def get_experiment(name: str) -> ExperimentConfig:
    if name not in EXPERIMENTS:
        raise ValueError(f"Experiment '{name}' not found. Available: {list_experiments()}")
    return EXPERIMENTS[name]

def list_experiments() -> List[str]:
    return list(EXPERIMENTS.keys())
