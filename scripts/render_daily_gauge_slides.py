"""Render only the new slide folder with the established shared-scene renderer."""
from pathlib import Path
import render_short_range_three_models as renderer

ROOT=Path(__file__).resolve().parents[1]
renderer.OUT=ROOT/'reports/daily_gauge_slides_2026_11_04'
renderer.PRIVATE=ROOT/'data/operational/daily_gauge_2026_11_04/slide_preview'
renderer.STEM='PBL6_DU_LIEU_NGAY_3_MO_HINH'

if __name__=='__main__':renderer.main()
