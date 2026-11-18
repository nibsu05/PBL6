"""Protect missing-data, summary-row and station-identity audit semantics."""
import copy
import unittest

from src.vrain_export_audit import inventory_from_groups, audit_history


def fixtures():
    groups=[dict(groupName='g', stats=[dict(stationID='A', stationUuid='uA', stationName='one', lat=16., lng=108., alt=None),
                                      dict(stationID='B', stationUuid='uB', stationName='two', lat=15., lng=108., alt=None)])]
    rows=[]
    for h in range(24):
        rows.append(dict(timePoint=f'{h:02d}:00 14/10', stations=[dict(id='A',sid='uA',name='one',depth='1.5'),
                                                               dict(id='B',sid='uB',name='two',depth='-')]))
    # Label is intentionally not the vendor's literal summary string.
    rows.insert(0,dict(timePoint='daily-summary',stations=[dict(id='A',sid='uA',name='one',depth='36'),
                                                         dict(id='B',sid='uB',name='two',depth='0')]))
    return groups,dict(stats=rows)


class VrainAuditTests(unittest.TestCase):
    def audit(self,payload,groups=None):
        if groups is None:groups,_=fixtures()
        return audit_history(payload,'2023-10-14',inventory_from_groups(groups))

    def test_summary_excluded_dash_not_zero_and_complete_sum(self):
        _,p=fixtures();r=self.audit(p)
        self.assertEqual(r['hourly_rows'],24)
        self.assertEqual(r['valid_numeric_cells'],24)
        self.assertEqual(r['missing_cells'],24)
        self.assertEqual(r['all24_complete_station_count'],1)
        self.assertEqual(r['no_hourly_values_station_count'],1)
        self.assertEqual(r['complete_station_summary_comparisons'],1)
        self.assertEqual(r['complete_station_sum_mismatches'],0)
        self.assertEqual(r['sum_tolerance_source_units'],1e-6)
        self.assertNotIn('sum_tolerance_mm',r)
        self.assertFalse(r['interval_timestamp_semantics_confirmed'])

    def test_zero_summary_without_hours_is_not_dry_day(self):
        _,p=fixtures();p['stats']=p['stats'][:1]
        for s in p['stats'][0]['stations']:s['depth']='0'
        r=self.audit(p)
        self.assertEqual(r['status'],'no_hourly_data')
        self.assertEqual(r['valid_numeric_cells'],0)
        self.assertEqual(r['missing_cells'],0)
        self.assertEqual(r['absent_hour_rows'],24)
        self.assertEqual(r['all24_complete_station_count'],0)
        self.assertEqual(r['complete_station_summary_comparisons'],0)

    def test_partial_station_not_used_for_sum_check(self):
        _,p=fixtures();p['stats'][1]['stations'][0]['depth']='-'
        r=self.audit(p)
        self.assertEqual(r['partial_station_count'],1)
        self.assertEqual(r['complete_station_summary_comparisons'],0)

    def test_sum_mismatch_reported_for_complete_station(self):
        _,p=fixtures();p['stats'][0]['stations'][0]['depth']='35'
        self.assertEqual(self.audit(p)['complete_station_sum_mismatches'],1)

    def test_duplicate_clock_or_station_or_conflicting_ids_rejected(self):
        _,base=fixtures()
        for mutation in ('clock','station','alias','membership'):
            p=copy.deepcopy(base)
            if mutation=='clock':p['stats'][2]['timePoint']=p['stats'][1]['timePoint']
            if mutation=='station':p['stats'][1]['stations'].append(copy.deepcopy(p['stats'][1]['stations'][0]))
            if mutation=='alias':p['stats'][1]['stations'][0]['sid']='wrong'
            if mutation=='membership':p['stats'][1]['stations'].pop()
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.audit(p)

    def test_nonfinite_negative_and_invalid_numbers_rejected(self):
        for bad in ('NaN','inf','-1','bad',None,True):
            _,p=fixtures();p['stats'][1]['stations'][0]['depth']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.audit(p)

    def test_current_inventory_duplicate_and_bad_coordinates_rejected(self):
        groups,_=fixtures();groups[0]['stats'].append(copy.deepcopy(groups[0]['stats'][0]))
        with self.assertRaises(ValueError):inventory_from_groups(groups)
        groups,_=fixtures();groups[0]['stats'][0]['lat']=float('nan')
        with self.assertRaises(ValueError):inventory_from_groups(groups)

    def test_2025_forbidden_and_incomplete_day_not_silently_accepted(self):
        g,p=fixtures()
        with self.assertRaises(ValueError):audit_history(p,'2025-10-14',inventory_from_groups(g))
        p['stats'].pop()
        with self.assertRaises(ValueError):self.audit(p)

    def test_name_match_does_not_create_id_crosswalk(self):
        g,p=fixtures()
        for item in g[0]['stats']:
            item['stationID']='current-'+item['stationID'];item['stationUuid']='current-'+item['stationUuid']
        r=self.audit(p,g)
        self.assertEqual(r['exact_current_station_id_matches'],0)
        self.assertEqual(r['current_unique_name_diagnostic_matches'],2)
        self.assertTrue(r['names_are_not_an_identity_crosswalk'])

    def test_legacy_id_inventory_can_match_without_name_join(self):
        original,p=fixtures();current=copy.deepcopy(original)
        for item in current[0]['stats']:
            item['stationID']='new-'+item['stationID'];item['stationUuid']='new-'+item['stationUuid']
        legacy=inventory_from_groups(original)
        r=audit_history(p,'2023-10-14',inventory_from_groups(current),legacy_inventory=legacy)
        self.assertEqual(r['exact_current_station_id_matches'],0)
        self.assertEqual(r['exact_v1_station_id_matches'],2)
        self.assertEqual(r['exact_v1_uuid_matches'],2)


if __name__=='__main__':unittest.main()
