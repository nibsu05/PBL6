"""Batch Python bổ sung 3 seed, không gọi LLM; dừng cây tiến trình tại hạn đã chỉ định.

Log/trạng thái/checkpoint nằm ngoài Git. Báo cáo sinh tự động để agent đọc khi quay lại.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-at", required=True, help="ISO timestamp có múi giờ")
    parser.add_argument("--cells", type=int, default=30)
    parser.add_argument("--output-name", default="pilot_bilstm_v2_3seeds")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--expand-danang", action="store_true", help="Sau 30 ô, chạy một batch riêng trên 93 ô")
    args = parser.parse_args()
    if not re.fullmatch(r"pilot_bilstm_v2_[A-Za-z0-9_-]+", args.output_name):
        parser.error("Tên đầu ra phải nằm trong nhóm pilot_bilstm_v2_*")
    deadline = datetime.fromisoformat(args.stop_at)
    if deadline.tzinfo is None:
        parser.error("--stop-at cần múi giờ")
    out = ROOT / "data/operational/offline_pilot_batch" / args.output_name
    out.mkdir(parents=True, exist_ok=True)
    status = {"stop_at": args.stop_at, "state": "starting", "llm_calls": 0}
    def save():
        status["updated_at"] = datetime.now(deadline.tzinfo).isoformat()
        (out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    if datetime.now(deadline.tzinfo) >= deadline:
        status["state"] = "deadline_reached"
        save()
        return
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # Giữ máy thức trong vòng đời batch.
    command = [sys.executable, "-u", str(ROOT / "scripts/pilot_bilstm_v2.py"),
               "--dataset-dir", "data/processed/dataset_v2_danang", "--seeds", "42", "43", "44",
               "--cells", str(args.cells), "--output-name", args.output_name]
    with (out / "process.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        status.update(state="running", pid=proc.pid)
        save()
        while proc.poll() is None:
            if datetime.now(deadline.tzinfo) >= deadline:
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
                status["state"] = "deadline_reached"
                save()
                return
            time.sleep(10)
        status.update(state="completed" if proc.returncode == 0 else "failed", returncode=proc.returncode)
    if proc.returncode == 0:
        import pandas as pd
        report = ROOT / "reports" / args.output_name
        run = json.loads((report / "run.json").read_text(encoding="utf-8"))
        if len(run["history"]) != 9 or run["test_2025_scored"]:
            status["state"] = "verification_failed"
            save()
            return
        scores = pd.read_csv(report / "scores.csv")
        subset = scores[(scores.season == "summer") & (scores.window == "0-3h") & scores.source.isin(["S0", "S1", "S4"])]
        lines = ["# Batch Bi LSTM ba seed tại Đà Nẵng", "", f"{args.cells} ô; S0/S1/S4; seed 42/43/44. Đây là ablation thông tin, chưa là so Bi-LSTM với TFT.",
                 "Không chấm test 2025. Mùa hè–thu, tổng 0–3 h; các hàng là trung bình dự báo của 3 seed.", "",
                 "| Cấu hình | CSI ≥10 mm | BSS ≥1 mm |", "| --- | ---: | ---: |"]
        for _, row in subset.iterrows():
            lines.append(f"| {row['source']} | {row['CSI>=10']:.4f} | {row['BSS>=1']:.4f} |")
        lines += ["", "Chi tiết và khoảng tin cậy: `scores.csv`, `paired_bootstrap.json`, `run.json`.",
                  "Báo cáo tự sinh; chưa có diễn giải mới của agent. Checkpoint/dự báo nằm ngoài Git."]
        (report / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if args.publish:
            try:
                for name in ("CLAUDE.md", "KE_HOACH_DU_AN.md"):
                    path = ROOT / name
                    text = path.read_text(encoding="utf-8")
                    marker = "<!-- OFFLINE_BATCH_STATUS -->"
                    updated = f"{marker} Batch 3 seed trên {args.cells} ô đã hoàn tất; bảng số liệu ở `reports/{args.output_name}/`. Chưa có diễn giải mới của agent; không chấm test 2025."
                    if sum(line.startswith(marker) for line in text.splitlines()) != 1:
                        raise ValueError(f"Không có marker trạng thái duy nhất trong {name}")
                    path.write_text("\n".join(updated if line.startswith(marker) else line for line in text.splitlines()) + "\n", encoding="utf-8")
                files = ["CLAUDE.md", "KE_HOACH_DU_AN.md", *[str((report / f).relative_to(ROOT)) for f in ("README.md", "scores.csv", "run.json", "paired_bootstrap.json")]]
                for command in (["git", "add", "--", *files], ["git", "commit", "-m", f"results: offline Bi-LSTM pilot {args.cells} cells, three seeds"], ["git", "push", "origin", "main"]):
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                    if result.returncode:
                        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
                status["publication"] = "pushed"
            except Exception as exc:
                status["publication"] = "failed"
                status["publication_error"] = str(exc)
    save()
    if status["state"] == "completed" and args.expand_danang and datetime.now(deadline.tzinfo) < deadline:
        command = [sys.executable, str(Path(__file__).resolve()), "--stop-at", args.stop_at, "--cells", "93",
                   "--output-name", "pilot_bilstm_v2_93cells_3seeds"]
        if args.publish:
            command.append("--publish")
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
