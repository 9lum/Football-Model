import unittest
from edge.game_history import merge_history
class HistoryTests(unittest.TestCase):
 def test_only_latest_pregame_forecast_is_saved_without_draws(self):
  p={'gameId':'g','kickoff':'2026-11-08T18:00Z','homePoints':20,'samples':[[20,10]]}
  h=merge_history({}, {'generatedAt':'2026-11-08T17:00Z','projections':[p]})
  self.assertNotIn('samples',h['projections'][0])
  self.assertEqual(merge_history(h,{'generatedAt':'2026-11-08T19:00Z','projections':[p|{'homePoints':40}]}),h)
  self.assertEqual(merge_history(h,{'generatedAt':'2026-11-08T16:00Z','projections':[p|{'homePoints':30}]}),h)
