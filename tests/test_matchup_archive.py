import unittest
from scripts.archive_matchup_research import eligible
class MatchupArchiveTests(unittest.TestCase):
 def test_publication_must_precede_kickoff_not_merely_model_generated_time(self):
  f={'gameId':'2026_09_CIN_ATL','kickoff':'2026-11-08T18:00Z'}
  self.assertIn(f['gameId'],eligible({'forecasts':[f]},{'issuedAt':'2026-11-08T17:59Z'}))
  self.assertFalse(eligible({'forecasts':[f]},{'issuedAt':'2026-11-08T18:00Z'}))
  self.assertFalse(eligible({'forecasts':[f]},{'issuedAt':'2026-11-08T18:01Z'}))
