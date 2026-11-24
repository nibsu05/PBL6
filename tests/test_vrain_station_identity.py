import unittest

from src.vrain_station_identity import canonical_inventory


def station(sid, name, lat, lon=108):
    return dict(station_id=sid, station_uuid='uuid-'+sid,
                station_name=name, latitude=lat, longitude=lon, altitude=None)


class IdentityTests(unittest.TestCase):
    def test_renaming_does_not_duplicate_station_and_extra_history_is_missing(self):
        old = [station('old', 'old name', 16)]
        new = [station('new', 'new name', 16), station('extra', 'extra', 17)]
        mapped = canonical_inventory(old, new)
        self.assertEqual(len(mapped), 2)
        self.assertEqual(mapped[0]['legacy_id'], 'old')
        self.assertFalse(mapped[0]['name_equal'])
        self.assertIsNone(mapped[1]['legacy_id'])
        self.assertFalse(mapped[0]['observation_equivalence_confirmed'])

    def test_duplicate_coordinates_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            canonical_inventory([station('old', 'a', 16)],
                                [station('one', 'a', 16), station('two', 'b', 16)])

    def test_same_name_cannot_override_location_and_order_is_stable(self):
        with self.assertRaisesRegex(ValueError, 'no exact'):
            canonical_inventory([station('old', 'same', 16)], [station('new', 'same', 17)])
        old = [station('a', 'a', 16)]
        new = [station('b', 'b', 17), station('c', 'a', 16)]
        self.assertEqual(canonical_inventory(old, new), canonical_inventory(old, new[::-1]))


if __name__ == '__main__':
    unittest.main()
