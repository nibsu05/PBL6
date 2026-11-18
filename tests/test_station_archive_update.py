from datetime import datetime,timedelta
import numpy as np
import unittest
from src.station_archive_update import parse_day,issue_contract,same_source_window,combine_hourly


def payload(day='2025-01-01',value=.2):
    marked=datetime.fromisoformat(day)
    rows=[dict(timePoint='Total',stations=[dict(id='a',depth=24*value)])]
    for k in range(24):
        t=marked-timedelta(hours=4)+timedelta(hours=k)
        rows.append(dict(timePoint=t.strftime('%H:%M %d/%m'),stations=[dict(id='a',depth=value)]))
    return dict(stats=rows)


def test_new_year_clock_and_last_complete_day():
    p=parse_day(payload(),'2025-01-01',{'a':'ST001'},['ST001','ST002'])
    assert str(p['times'][0])=='2024-12-31 20:00:00'
    assert str(p['times'][-1])=='2025-01-01 19:00:00'
    assert p['valid'][:,0].all() and not p['valid'][:,1].any()
    with unittest.TestCase().assertRaises(ValueError):parse_day(payload('2026-11-16'),'2026-11-16',{'a':'ST001'},['ST001'])


def test_sum_mismatch_retains_original_but_disables_label():
    j=payload();j['stats'][0]['stations'][0]['depth']=99
    p=parse_day(j,'2025-01-01',{'a':'ST001'},['ST001'])
    assert p['raw'][:,0].sum()>0 and not p['valid'].any()
    assert p['bad_daily_sum'][0]


def test_missing_hourly_value_does_not_become_zero():
    j=payload();j['stats'][5]['stations'][0]['depth']='-'
    p=parse_day(j,'2025-01-01',{'a':'ST001'},['ST001'])
    assert np.isnan(p['raw'][4,0]) and not p['valid'][4,0]
    assert p['metadata']['complete_qc_station_days']==0


def test_duplicate_unknown_station_or_shifted_clock_fails():
    j=payload();j['stats'][-1]['timePoint']=j['stats'][-2]['timePoint']
    with unittest.TestCase().assertRaises(ValueError):parse_day(j,'2025-01-01',{'a':'ST001'},['ST001'])
    with unittest.TestCase().assertRaises(ValueError):parse_day(payload(),'2025-01-01',{'b':'ST001'},['ST001'])
    j=payload();j['stats'][-1]['timePoint']='20:00 01/01'
    with unittest.TestCase().assertRaises(ValueError):parse_day(j,'2025-01-01',{'a':'ST001'},['ST001'])


def test_empty_day_remains_missing():
    j=payload();j['stats']=j['stats'][:1]
    p=parse_day(j,'2025-01-01',{'a':'ST001'},['ST001'])
    assert not p['valid'].any() and np.isnan(p['raw']).all()


def test_forecast_contract_and_source_transition():
    init,issue=issue_contract('2025-01-01')
    assert issue-init==__import__('pandas').Timedelta(hours=12)
    with unittest.TestCase().assertRaises(ValueError):issue_contract('2026-11-13')
    assert same_source_window([0,0,0],0,3)
    assert not same_source_window([0,1,1],0,3)
    assert not same_source_window([0,-1,0],0,3)
    assert not same_source_window([3,3,3],0,3)


def test_conflicting_channels_are_not_averaged_or_summed():
    rain,code,conflict=combine_hourly([2,0,4,np.nan],[3,0,np.nan,5],[True,True,True,False],[True,True,False,True])
    assert np.isnan(rain[0]) and conflict[0] and code[0]==3
    np.testing.assert_array_equal(rain[1:],[0,4,5])
    np.testing.assert_array_equal(code,[3,0,0,1])


def test_temporal_roles_exclude_windows_crossing_year_splits():
    import pandas as pd
    from scripts.build_station_update import split_for_issue
    assert split_for_issue(pd.Timestamp('2024-12-28T12:00Z'))=='dev'
    assert split_for_issue(pd.Timestamp('2024-12-29T12:00Z'))=='boundary'
    assert split_for_issue(pd.Timestamp('2025-01-01T12:00Z'))=='reserved2025'
    assert split_for_issue(pd.Timestamp('2026-01-01T12:00Z'))=='external2026'


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value) for name,value in globals().items() if name.startswith('test_') and callable(value))


if __name__=='__main__':unittest.main()
