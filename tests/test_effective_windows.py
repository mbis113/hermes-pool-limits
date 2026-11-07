import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('pool_usage', Path(__file__).resolve().parents[1] / 'pool_usage.py')
usage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(usage)


class EffectiveWindowsTests(unittest.TestCase):
    def test_monthly_exhaustion_masks_five_hours(self):
        windows = [['5 часов', 0.0, 100], ['Месяц', 100.0, 200]]
        self.assertEqual(usage._effective_windows(windows, now=50),
                         [['5 часов', 100.0, 100], ['Месяц', 100.0, 200]])
        self.assertEqual(windows[0][1], 0.0)

    def test_weekly_exhaustion_masks_five_hours(self):
        self.assertEqual(usage._effective_windows([['5 часов', 15.0, 100], ['Неделя', 100.0, 200]], now=50)[0][1], 100.0)

    def test_reset_restores_short_window_without_stale_block(self):
        windows = [['5 часов', 20.0, 300], ['Неделя', 100.0, 200]]
        self.assertEqual(usage._effective_windows(windows, now=200)[0][1], 20.0)
        self.assertEqual(usage._effective_windows([['5 часов', 20.0, 300], ['Неделя', 5.0, 400]], now=201)[0][1], 20.0)

    def test_not_near_zero_and_missing_data(self):
        self.assertEqual(usage._effective_windows([['5 часов', 0.0, 100], ['Неделя', 99.7, 200]], now=50)[0][1], 0.0)
        self.assertEqual(usage._effective_windows([['5 часов', 0.0, 100], ['Неделя', None, 200]], now=50)[0][1], 0.0)


if __name__ == '__main__':
    unittest.main()
