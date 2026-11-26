import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from matching import score_pair


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.lost=dict(category='backpack',custom_category=None,date='2026-10-12',title='Blue backpack',description='Yellow star patch',location='Library lobby')

    def test_positive_and_explanations(self):
        score,reasons=score_pair(self.lost,dict(self.lost,date='2026-10-13'))
        self.assertEqual(score,100)
        self.assertEqual(len(reasons),4)

    def test_date_category_and_unrelated_details(self):
        for changes in [dict(category='phone'),dict(date='2026-10-10'),dict(date='2026-11-12'),
                        dict(title='Black backpack',description='Leather bag',location='Gym')]:
            self.assertIsNone(score_pair(self.lost,dict(self.lost,**changes)))

    def test_other_needs_shared_custom_type(self):
        lost=dict(self.lost,category='other',custom_category='Graduation tassel')
        self.assertIsNone(score_pair(lost,dict(lost,custom_category='Chess set')))
        self.assertIsNotNone(score_pair(lost,dict(lost,custom_category='Blue tassel')))

    def test_case_and_date_boundaries(self):
        self.assertIsNotNone(score_pair(self.lost,dict(self.lost,date='2026-10-11',location='LIBRARY LOBBY')))
        self.assertIsNotNone(score_pair(self.lost,dict(self.lost,date='2026-11-11')))


if __name__=='__main__':
    unittest.main()
