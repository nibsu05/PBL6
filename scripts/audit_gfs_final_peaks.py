"""Post-test structural replay of largest labels; never change samples/scores."""
from pathlib import Path
import gzip
import json
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from src.gfs_final import BASE, PUBLIC
from src.gfs_daily import sha, write_json
from src.gfs_final_gate import check_manifest


def main():
    check_manifest()
    frame = pd.read_parquet(BASE / "holdout_predictions_private.parquet")
    registry = pd.read_csv(ROOT / "data/operational/vrain_update_2026_11_16/station_registry_private.csv",
                           dtype={"legacy_id": str, "modern_id": str}).set_index("canonical_id")
    records = []
    for scope, group in frame.groupby("evaluation_set"):
        candidates = group.sort_values("y_mm", ascending=False).drop_duplicates(["station_id", "target_end_utc"]).head(12)
        for row in candidates.itertuples():
            day = row.target_end_utc.tz_convert("Asia/Ho_Chi_Minh").strftime("%Y-%m-%d")
            channel = row.gauge_namespace
            alias = str(registry.loc[row.station_id, channel+"_id"])
            file = ROOT / "data/operational/vrain_update_2026_11_16/raw" / channel / day[:4] / (day+".json.gz")
            payload = json.loads(gzip.decompress(file.read_bytes()))
            hourly = []
            totals = []
            for line in payload["stats"]:
                values = [s["depth"] for s in line["stations"] if str(s["id"]) == alias]
                if len(values) != 1 or values[0] in (None, "-"):
                    raise ValueError("Missing or duplicate source item for a ready peak")
                if re.fullmatch(r"\d{2}:\d{2} \d{2}/\d{2}", line["timePoint"].strip()):
                    hourly.append(float(values[0]))
                else:
                    totals.append(float(values[0]))
            if len(hourly) != 24 or len(totals) != 1:
                raise ValueError("Peak source day does not have24hours and one summary")
            np.testing.assert_allclose(sum(hourly), row.y_mm, rtol=2e-6, atol=1e-3)
            np.testing.assert_allclose(totals[0], row.y_mm, rtol=2e-6, atol=1e-3)
            records.append(dict(evaluation_set=scope, station_id=row.station_id, day=day,
                y_mm=float(row.y_mm), hourly_sum_mm=sum(hourly), provider_total_mm=totals[0], source_sha256=sha(file)))
    pd.DataFrame(records).to_csv(BASE / "peak_label_replays_private.csv", index=False)
    write_json(PUBLIC / "peak_label_audit.json", dict(status="passed_structural_only", posthoc_diagnostic=True,
        labels_checked=len(records), each_has24numeric_source_hours=True, hourly_sums_and_provider_totals_match=True,
        maximum_test2025_mm=float(frame.loc[frame.evaluation_set.eq("test2025_legacy"), "y_mm"].max()),
        physical_sensor_validation=False, observations_removed=0, predictions_or_scores_changed=False,
        source_replay_details_private=True))
    print(json.dumps(dict(status="passed_structural_only", labels=len(records))), flush=True)


if __name__ == "__main__":
    main()
