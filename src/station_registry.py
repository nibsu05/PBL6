"""Danh mục trạm synop NOAA (ISD/GSOD) dùng để kiểm chứng độc lập.

Toạ độ lấy từ NOAA ``isd-history.csv``. Tỉnh ghi theo ranh giới mới
(Nghị quyết 202/2025/QH15). Dữ liệu NOAA của mọi trạm Việt Nam hiện kết thúc
ngày 24/08/2025, nên kiểm chứng bằng trạm chỉ phủ đến mốc đó.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    usaf: str
    name: str
    lat: float
    lon: float
    elev_m: float
    province: str
    region: str

    @property
    def gsod_id(self) -> str:
        return f"{self.usaf}99999"


STATIONS: tuple[Station, ...] = (
    Station("488480", "Đồng Hới", 17.483, 106.600, 8.0, "Quảng Trị", "Bắc Trung Bộ"),
    Station("488520", "Phú Bài (Huế)", 16.402, 107.703, 14.6, "Huế", "Trung Trung Bộ"),
    Station("488550", "Đà Nẵng", 16.044, 108.199, 10.1, "Đà Nẵng", "Trung Trung Bộ"),
    Station("488630", "Quảng Ngãi", 15.133, 108.783, 9.0, "Quảng Ngãi", "Trung Trung Bộ"),
    Station("488200", "Nội Bài", 21.221, 105.807, 11.9, "Hà Nội", "Bắc Bộ"),
    Station("488250", "Hà Đông", 20.967, 105.767, 7.9, "Hà Nội", "Bắc Bộ"),
    Station("488660", "Pleiku", 14.005, 108.017, 741.9, "Gia Lai", "Tây Nguyên"),
    Station("488750", "Buôn Ma Thuột", 12.683, 108.083, 537.0, "Đắk Lắk", "Tây Nguyên"),
    Station("488700", "Quy Nhơn", 13.767, 109.217, 6.0, "Gia Lai", "Nam Trung Bộ"),
    Station("488770", "Nha Trang", 12.250, 109.200, 10.0, "Khánh Hòa", "Nam Trung Bộ"),
    Station("488940", "Nhà Bè", 10.650, 106.717, 3.6, "TP.HCM", "Nam Bộ"),
    Station("489125", "Cần Thơ", 10.083, 105.717, 3.1, "Cần Thơ", "Nam Bộ"),
)

BY_USAF = {s.usaf: s for s in STATIONS}
