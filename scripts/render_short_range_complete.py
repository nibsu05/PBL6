"""Render the new complete report using the same checked HTML scene renderer."""
from pathlib import Path
import render_short_range_three_models as renderer

ROOT=Path(__file__).resolve().parents[1]
renderer.OUT=ROOT/'reports/short_range_complete_2026_10_28'
renderer.PRIVATE=ROOT/'data/operational/short_range/complete_preview_2026_10_28'
renderer.STEM='PBL6_SO_SANH_3_MO_HINH_DAY_DU'

if __name__=='__main__':renderer.main()
