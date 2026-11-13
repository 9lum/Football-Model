import unittest
import datetime as dt
from scripts.pregame_weather import due_games,refresh_result,UTC
class PregameWeatherTests(unittest.TestCase):
 def setUp(self):
  self.kickoff=dt.datetime(2026,11,15,18,tzinfo=UTC);self.g={'gameId':'2026_10_MIN_GB','kickoff':self.kickoff.isoformat()}
 def test_window_and_successful_runs_are_deduplicated(self):
  self.assertEqual(due_games([self.g],{},self.kickoff-dt.timedelta(minutes=36)),[])
  self.assertEqual(len(due_games([self.g],{},self.kickoff-dt.timedelta(minutes=35))),1)
  self.assertEqual(due_games([self.g],{self.g['gameId']:{'kickoff':self.g['kickoff'],'deadlineMet':True}},self.kickoff-dt.timedelta(minutes=20)),[])
  self.assertEqual(due_games([self.g],{},self.kickoff),[])
 def test_only_fresh_and_on_time_publication_passes(self):
  collected=self.kickoff-dt.timedelta(minutes=18);forecast={'status':'ok','retrievedAt':collected.isoformat()}
  self.assertTrue(refresh_result(self.g,forecast,collected,self.kickoff-dt.timedelta(minutes=15))['deadlineMet'])
  self.assertFalse(refresh_result(self.g,forecast,collected,self.kickoff-dt.timedelta(minutes=14))['deadlineMet'])
  self.assertFalse(refresh_result(self.g,{},collected,collected)['deadlineMet'])
  self.assertFalse(refresh_result(self.g,{'status':'ok','retrievedAt':(collected-dt.timedelta(hours=1)).isoformat()},collected,collected)['deadlineMet'])
 def test_rescheduled_kickoff_is_eligible_again(self):
  old={self.g['gameId']:{'kickoff':(self.kickoff-dt.timedelta(hours=1)).isoformat(),'deadlineMet':True}}
  self.assertEqual(len(due_games([self.g],old,self.kickoff-dt.timedelta(minutes=20))),1)
