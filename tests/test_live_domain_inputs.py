import copy,unittest
import numpy as np
from src.live_domain_inputs import wind_uv,specific_humidity_gkg,weather_frame
def payloads():
    units={'temperature_2m':'°C','dew_point_2m':'°C','relative_humidity_2m':'%','surface_pressure':'hPa',
           'pressure_msl':'hPa','wind_speed_10m':'m/s','wind_direction_10m':'°',
           'cloud_cover':'%','cloud_cover_low':'%','cloud_cover_mid':'%','cloud_cover_high':'%',
           'total_column_integrated_water_vapour':'kg/m²'}
    sh={'time':['2026-10-13T00:00'],**{f:[50.] for f in units}}
    sh['surface_pressure']=[1000.];sh['pressure_msl']=[1010.]
    sh['wind_speed_10m']=[10.];sh['wind_direction_10m']=[90.]
    pu={'temperature_850hPa':'°C','relative_humidity_850hPa':'%',
        'wind_speed_850hPa':'m/s','wind_direction_850hPa':'°'}
    ph=dict(time=sh['time'].copy(),temperature_850hPa=[20.],relative_humidity_850hPa=[50.],
            wind_speed_850hPa=[10.],wind_direction_850hPa=[0.])
    return {'hourly':sh,'hourly_units':units},{'hourly':ph,'hourly_units':pu}
class LiveInputTest(unittest.TestCase):
    def test_meteorological_direction(self):
        u,v=wind_uv([10,10,10,10],[0,90,180,270])
        np.testing.assert_allclose(u,[0,-10,0,10],atol=1e-12)
        np.testing.assert_allclose(v,[-10,0,10,0],atol=1e-12)
    def test_specific_humidity_known_thermodynamic_value(self):
        self.assertAlmostEqual(float(specific_humidity_gkg(20,50)),8.595,delta=.02)
        self.assertEqual(float(specific_humidity_gkg(20,0)),0)
        with self.assertRaises(ValueError):specific_humidity_gkg(20,101)
    def test_timestamp_mismatch_is_rejected_before_any_fill(self):
        a,b=payloads();b['hourly']['time']=['2026-10-13T01:00']
        with self.assertRaisesRegex(ValueError,'thời gian'):weather_frame(a,b)
    def test_missing_850_never_filled_zero(self):
        a,b=payloads();b['hourly']['wind_speed_850hPa']=[None]
        with self.assertRaisesRegex(ValueError,'NaN wind_speed_850'):weather_frame(a,b)
    def test_percent_cloud_and_ms_wind_are_converted(self):
        a,b=payloads();frame=weather_frame(a,b)
        self.assertEqual(frame.tcc.iloc[0],.5)
        self.assertEqual(frame.u10.iloc[0],-10)
        self.assertEqual(frame.v850.iloc[0],-10)
        self.assertAlmostEqual(frame.q850_gkg.iloc[0],8.595,delta=.02)
    def test_wrong_wind_unit_rejected(self):
        a,b=payloads();a['hourly_units']['wind_speed_10m']='km/h'
        with self.assertRaisesRegex(ValueError,'đơn vị wind_speed_10m'):weather_frame(a,b)
if __name__=='__main__':unittest.main()
