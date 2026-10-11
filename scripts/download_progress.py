"""Theo dõi tiến độ tải dữ liệu Earth Engine: số khối, tốc độ 10 phút gần nhất, thời gian còn lại.

Chạy một lần:      python scripts/download_progress.py
Tự làm mới 60 s:  python scripts/download_progress.py --watch 60
"""

from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOBS = {  # tên: (thư mục khối, tổng số khối dự kiến)
    "GSMaP lưới (nhãn + quan trắc)": (ROOT / "data/raw_data/gee/gsmap/grid", 555),
    "ERA5 lưới (33 biến)": (ROOT / "data/raw_data/gee/era5/grid", 1128),
}
WINDOW_S = 600


def report() -> str:
    now = time.time()
    lines = [f"Tiến độ tải dữ liệu — {datetime.now():%H:%M:%S}"]
    for name, (folder, total) in JOBS.items():
        files = list(folder.glob("*.parquet")) if folder.exists() else []
        done = min(len(files), total)
        recent = sum(1 for f in files if now - f.stat().st_mtime <= WINDOW_S)
        rate = recent / (WINDOW_S / 60)  # khối/phút
        pct = 100 * done / total
        bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
        if done >= total:
            eta = "xong"
        elif rate > 0:
            finish = datetime.now() + timedelta(minutes=(total - done) / rate)
            eta = f"còn ~{(total - done) / rate:.0f} phút (xong lúc ~{finish:%H:%M})"
        else:
            eta = "không có khối mới trong 10 phút — tiến trình có thể đã dừng"
        lines.append(f"  {name:32s} {bar} {done:4d}/{total} ({pct:5.1f}%)  {rate:4.1f} khối/phút  {eta}")
    procs = subprocess.run(["pgrep", "-f", "extract_gee_"], capture_output=True, text=True).stdout.split()
    lines.append(f"  Tiến trình tải đang chạy: {len(procs)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--watch", type=int, default=0, help="Số giây giữa các lần làm mới (0 = chạy một lần)")
    args = parser.parse_args()
    if not args.watch:
        print(report())
        return
    try:
        while True:
            print("\033[2J\033[H" + report() + "\n\n(Ctrl+C để thoát)", flush=True)
            time.sleep(args.watch)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
