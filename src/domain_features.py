"""Biểu diễn gió ẩm và địa hình: chỉ dùng cửa sổ quá khứ đã có.

Các đại lượng là proxy, không phải lượng mưa hoặc IVT vật lý đầy đủ.
RAW và DOMAIN có cùng input_dim nhờ bốn cột padding ở RAW.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import numpy as np
from src.dataloader_v2 import WindowSampler, epoch_subset

RAW_NAMES = ('tcwv', 'u850', 'v850', 'q850_gkg')
DERIVED_NAMES = ('ne_moisture_index', 'ne_terrain_index', 'ne_persistence24', 'above_ground850')


def physical_indices(q_gkg, u, v, pressure_hpa, upslope_m, latitude):
    """[N,W] weather + [N] static -> [N,W,4], forecast-causal.

    Persistence dùng toàn bộ lịch sử W giờ, đều biết trước giờ phát hành.
    Gió đông bắc thổi về tây nam: u,v âm. Địa hình là chênh cao một ô NE.
    Khi 850 hPa nằm dưới bề mặt (sp<850), proxy flux=0 và có cờ riêng.
    """
    above = pressure_hpa >= 850
    inland = np.maximum(-(u + v) / np.sqrt(2.0), 0.0)
    moisture = np.maximum(q_gkg, 0.0) / 1000.0 * inland * above
    distance = 111_320.0 * 0.1 * np.sqrt(1 + np.cos(np.deg2rad(latitude)) ** 2)
    slope = np.maximum(upslope_m, 0.0) / distance
    terrain = moisture * slope[:, None]
    persistence = np.broadcast_to(((inland > 0) & above).mean(axis=1)[:, None], u.shape)
    return np.stack((moisture, terrain, persistence, above.astype(float)), axis=-1).astype(np.float32)


@dataclass
class DerivedNormalizer:
    mean: list[float]
    std: list[float]

    def transform(self, x):
        return ((x - np.asarray(self.mean, dtype=np.float32)) /
                np.asarray(self.std, dtype=np.float32)).astype(np.float32)

    def save(self, path):
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding='utf-8')


class DomainSampler:
    def __init__(self, base: WindowSampler, kind='padding', derived_norm=None, derived_mask=None):
        if kind not in ('padding', 'domain'):
            raise ValueError('kind phải là padding hoặc domain')
        mask = np.ones(4, dtype=np.float32) if derived_mask is None else np.asarray(derived_mask, np.float32)
        if mask.shape != (4,) or not np.isin(mask, [0, 1]).all():
            raise ValueError('derived_mask phải có 4 phần tử 0/1')
        self.derived_mask = mask
        self.base, self.kind, self.derived_norm = base, kind, derived_norm
        self.cfg, self.ds = base.cfg, base.ds
        self.future_names = base.future_names
        self.x_past_names = base.x_past_names + list(DERIVED_NAMES)

    def _raw(self, x, name):
        pos = self.base.past_names.index(name)
        # Các biến cần dùng ở đây đều z-score tuyến tính, không log1p.
        return x[..., pos] * self.base.norm.std[name] + self.base.norm.mean[name]

    def derived(self, batch):
        x = batch['x_past']
        cells = self.ds.cells.iloc[batch['cell']]
        return physical_indices(self._raw(x, 'q850_gkg'), self._raw(x, 'u850'),
                                self._raw(x, 'v850'), self._raw(x, 'sp_hpa'),
                                cells.ne_upslope_m.to_numpy(float), cells.lat.to_numpy(float))

    def batch(self, index):
        out = self.base.batch(index)
        extra = np.zeros((*out['x_past'].shape[:2], 4), dtype=np.float32)
        if self.kind == 'domain':
            extra = self.derived(out)
            if self.derived_norm is not None:
                extra = self.derived_norm.transform(extra)
            if not np.isfinite(extra).all():
                raise ValueError('Đặc trưng domain không hữu hạn; không tự điền dữ liệu thiếu')
        # Mask sau chuẩn hóa: cột bị bỏ thành hằng0, giữ kích thước/tham số.
        extra = extra * self.derived_mask
        out['x_past'] = np.concatenate((out['x_past'], extra), axis=-1)
        return out

    @classmethod
    def fit_derived(cls, base, train_index, train_years, n=3000, seed=2026):
        years = set(train_years)
        ds, cfg = base.ds, base.cfg
        if (not set(ds.hours[train_index[:, 1]].year).issubset(years) or
                not set(ds.hours[train_index[:, 1] + cfg.horizon - 1].year).issubset(years)):
            raise ValueError('Chuẩn hóa domain chỉ được fit trên nhãn thuộc năm train')
        pick = epoch_subset(train_index, n, seed)
        temporary = cls(base, 'domain')
        blocks = [temporary.derived(base.batch(pick[i:i+256])) for i in range(0, len(pick), 256)]
        x = np.concatenate(blocks).reshape(-1, 4)
        if not np.isfinite(x).all():
            raise ValueError('Thiếu input domain trong train')
        std = x.std(0)
        return DerivedNormalizer(x.mean(0).tolist(), np.where(std > 1e-8, std, 1).tolist())
