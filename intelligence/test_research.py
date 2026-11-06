import unittest
from intelligence.research import simulate,settle,closing_line_value,summarize
class ResearchTests(unittest.TestCase):
    def test_pushes_and_dnp_are_not_wins(self):
        self.assertEqual(settle(0,1,'Under',-110,False)['status'],'void');self.assertEqual(settle(5,5,'Over',100)['status'],'push');self.assertIsNone(settle(None,5,'Over',100)['returnPerUnit'])
    def test_probability_threshold(self):
        self.assertFalse(summarize([100]*69+[0]*31,50,'Over',-110)['meetsProbabilityThreshold']);self.assertTrue(summarize([100]*70+[0]*30,50,'Over',-110)['meetsProbabilityThreshold'])
    def test_bootstrap_is_explicit_and_reproducible(self):
        a=simulate(list(range(100)),50,'Over',-110);self.assertEqual(a['draws'],10000);self.assertEqual(a,simulate(list(range(100)),50,'Over',-110));self.assertIn('do not create',a['method']);self.assertIsNone(closing_line_value(-110,-120,50,51))
