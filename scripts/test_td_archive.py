import unittest
from edge.td_archive import retain_pregame_game
class ArchiveTests(unittest.TestCase):
 def test_preserves_only_actual_pregame_predictions_across_repeated_refreshes(self):
  game={'gameId':'g','kickoff':'2026-11-08T18:00Z','players':[{'playerId':'a','quotes':[{'qualified':True}]}]}
  old={'generatedAt':'2026-11-08T17:00Z','games':[game]}
  saved=retain_pregame_game(old,'g',game['kickoff']);self.assertIsNotNone(saved);self.assertFalse(saved['players'][0]['quotes'][0]['qualified'])
  self.assertTrue(game['players'][0]['quotes'][0]['qualified'])
  next_report={'generatedAt':'2026-11-08T19:00Z','games':[saved]}
  self.assertEqual(retain_pregame_game(next_report,'g',game['kickoff'])['pregameGeneratedAt'],old['generatedAt'])
  self.assertIsNone(retain_pregame_game({'generatedAt':'2026-11-08T19:00Z','games':[game]},'g',game['kickoff']))
  self.assertIsNone(retain_pregame_game(old,'other',game['kickoff']))
