r"""Đóng gói / kiểm tra dữ liệu nguồn của pipeline v2 để chuyển máy qua Google Drive.

Chỉ đóng gói dữ liệu *nguồn* (khó hoặc lâu tạo lại: phải tải từ Earth Engine, NOAA,
Open-Meteo). Dataset v2 (~12 GB) được dựng lại từ nguồn trong khoảng 3 phút nên không
đóng gói. Danh sách file kèm SHA-256 ghi vào ``data/DATA_MANIFEST_v2.json`` (nhỏ, commit
vào git) để máy mới kiểm tra đã tải đủ và không hỏng.

Đóng gói (máy cũ):
    python scripts/package_data.py pack --out ~/Downloads/pbl6_data_v2.tar
Kiểm tra sau khi giải nén ở thư mục gốc repo (máy mới):
    tar -xf pbl6_data_v2.tar
    python scripts/package_data.py verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "DATA_MANIFEST_v2.json"
SOURCES = [  # đường dẫn tương đối từ gốc repo
    "data/raw_data/gee/gsmap/grid",         # nhãn + quan trắc trên lưới 0,1°
    "data/raw_data/gee/era5/grid",          # ERA5 33 biến trên lưới 0,25°
    "data/raw_data/gee/gsmap/stations",     # Thí nghiệm 0
    "data/raw_data/gee/imerg/stations",
    "data/processed/gee/static_cells.parquet",
    "data/processed/stations",              # GSOD đã QC, Open-Meteo, vệ tinh tại trạm
    "data/raw_data/gsod",
    "data/raw_data/openmeteo_baselines",
]


def _files() -> list[Path]:
    out: list[Path] = []
    for rel in SOURCES:
        path = ROOT / rel
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            out += sorted(p for p in path.rglob("*") if p.is_file() and p.name != ".DS_Store")
        else:
            print(f"Cảnh báo: thiếu {rel}", file=sys.stderr)
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pack(out: Path) -> None:
    files = _files()
    entries = {str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": _sha256(p)} for p in files}
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archive": out.name, "n_files": len(entries),
        "total_bytes": sum(e["bytes"] for e in entries.values()),
        "rebuild": ["python scripts/build_dataset_v2.py --years 2015 2026",
                    "python -c \"from src.dataloader_v2 import build_cell_major; build_cell_major()\""],
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, "w") as tar:          # parquet đã nén sẵn, không nén thêm
        for p in files:
            tar.add(p, arcname=str(p.relative_to(ROOT)))
        tar.add(MANIFEST, arcname=str(MANIFEST.relative_to(ROOT)))
    print(f"Đã ghi {out} ({manifest['total_bytes'] / 1e9:.2f} GB, {len(entries)} file) và {MANIFEST.relative_to(ROOT)}")


def verify() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing, bad = [], []
    for rel, meta in manifest["files"].items():
        path = ROOT / rel
        if not path.exists():
            missing.append(rel)
        elif path.stat().st_size != meta["bytes"] or _sha256(path) != meta["sha256"]:
            bad.append(rel)
    print(f"{manifest['n_files'] - len(missing) - len(bad)}/{manifest['n_files']} file khớp; "
          f"thiếu {len(missing)}, sai {len(bad)}")
    for rel in (missing + bad)[:20]:
        print("  ", rel)
    if missing or bad:
        sys.exit(1)
    print("Dữ liệu đủ. Dựng lại dataset v2:\n  " + "\n  ".join(manifest["rebuild"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--out", type=Path, required=True)
    sub.add_parser("verify")
    args = parser.parse_args()
    pack(args.out.expanduser()) if args.cmd == "pack" else verify()


if __name__ == "__main__":
    main()
