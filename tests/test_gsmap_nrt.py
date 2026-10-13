import gzip,unittest
import numpy as np
import pandas as pd
from src.gsmap_nrt import decode_nrt_binary,native_indices,features_for_context,interval_from_filename,SHAPE
from scripts.probe_gsmap_nrt_point import parse_point

class NRTTest(unittest.TestCase):
    def test_grid_axis_byte_order_and_missing(self):
        raw=np.zeros(SHAPE,dtype='<f4');raw[439,1081]=6.06;raw[440,1081]=-999.9
        grid=decode_nrt_binary(gzip.compress(raw.tobytes()))
        self.assertAlmostEqual(float(grid[439,1081]),6.06,places=5)
        self.assertTrue(np.isnan(grid[440,1081]))
        i,j=native_indices([16.05],[108.15])
        self.assertEqual((int(i[0]),int(j[0])),(439,1081))
        with self.assertRaises(ValueError):native_indices([16.],[108.2])
        with self.assertRaises(ValueError):decode_nrt_binary(b'bad')
    def test_context_mask_matches_training_instead_of_all25pixels(self):
        grid=np.zeros(SHAPE,dtype=np.float32)
        i,j=native_indices([16.05]*3,[108.15,108.25,108.35]);grid[i,j]=[1,3,100]
        context=pd.DataFrame(dict(site=['a','b'],lat=[16.05]*2,lon=[108.15,108.25]))
        f=features_for_context(grid,context,['a'])
        self.assertEqual(float(f.gsmap_nb5_mean_mm.iloc[0]),2)
        self.assertEqual(float(f.gsmap_nb5_max_mm.iloc[0]),3)
    def test_raw_filename_interval_and_reject_gauge(self):
        lo,hi=interval_from_filename('gsmap_nrt.20261012.0800.dat.gz')
        self.assertEqual(hi-lo,pd.Timedelta(hours=1))
        self.assertEqual(lo.hour,8)
        with self.assertRaises(ValueError):interval_from_filename('gsmap_gauge.20261012.0800.dat.gz')
    def test_point_popup_schema_and_timestamp(self):
        text='<h4>2026/10/12 08:00 (UTC)</h4>Latitude: 16.050000<br>Longitude: 108.150000<br><h5>Rain:</h5><div>6.06 mm/hr</div>'
        actual=parse_point(text,'2026-10-12T08:00Z',16.05,108.15)
        self.assertEqual(actual['rain_rate_mm_h'],6.06)
        with self.assertRaises(ValueError):parse_point(text,'2026-10-12T09:00Z',16.05,108.15)
if __name__=='__main__':unittest.main()
