import unittest
from scripts.refresh_bdl_props import normalize
class BdlPropTests(unittest.TestCase):
 def test_exact_types_only_and_no_atdd_or_milestone_substitution(self):
  event={'home_team':'A','away_team':'B'};players={1:{'first_name':'Test','last_name':'Player','team':{'full_name':'A'}}};row={'player_id':1,'vendor':'draftkings','prop_type':'rushing_tds','line_value':'0.5','market':{'type':'over_under','over_odds':130,'under_odds':-150},'updated_at':'2026-11-07T19:00:00Z'}
  result=normalize([row,{**row,'prop_type':'anytime_td'},{**row,'market':{'type':'milestone','odds':150}}],players,event)
  m=result['bookmakers'][0]['markets'];self.assertEqual(len(m),1);self.assertEqual(m[0]['key'],'player_rush_tds');self.assertEqual(len(m[0]['outcomes']),2);self.assertEqual(m[0]['timestampType'],'provider_refresh')
 def test_unmatched_names_teams_and_half_game_props_excluded(self):
  event={'home_team':'A','away_team':'B'};row={'player_id':1,'vendor':'draftkings','prop_type':'passing_tds_1h'};self.assertFalse(normalize([row],{},event)['bookmakers'])
