import datetime as dt
import unittest
from scripts.refresh_public_game_odds import parse
class PublicOddsTests(unittest.TestCase):
 def test_prices_are_explicit_and_observation_is_not_provider_time(self):
  payload={'events':[{'id':'one','date':'2026-11-08T18:00Z','status':{'type':{'completed':False}},'competitions':[{'competitors':[{'homeAway':'home','team':{'displayName':'Home'}},{'homeAway':'away','team':{'displayName':'Away'}}],'odds':[{'provider':{'id':100,'name':'DraftKings'},'moneyline':{'home':{'close':{'odds':'-150'}}},'pointSpread':{'home':{'close':{'line':'-3','odds':'-110'}}},'total':{'over':{'close':{'line':'o44.5','odds':'-105'}}}}]}]}]}
  rows=parse(payload,'2026-11-06T00:00:00Z',dt.datetime(2026,11,6,tzinfo=dt.timezone.utc));b=rows[0]['bookmakers'][0];self.assertIsNone(b['last_update']);self.assertEqual(b['markets'][2]['outcomes'][0]['point'],44.5);self.assertEqual(b['markets'][0]['outcomes'][0]['price'],-150);self.assertEqual(len(b['markets'][0]['outcomes']),1)
 def test_final_results_require_explicit_completed_status_and_both_scores(self):
  from scripts.refresh_public_game_odds import parse_results
  event={'id':'one','date':'2026-11-08T18:00Z','status':{'type':{'completed':False,'state':'in'}},'competitions':[{'competitors':[{'homeAway':'home','team':{'displayName':'Home'},'score':'0'},{'homeAway':'away','team':{'displayName':'Away'},'score':'24'}]}]}
  payload={'events':[event]};self.assertFalse(parse_results(payload,'now')[0]['completed'])
  event['status']['type']['completed']=True;row=parse_results(payload,'now')[0];self.assertTrue(row['completed']);self.assertEqual(row['homeScore'],0)
  event['competitions'][0]['competitors'][0].pop('score');self.assertFalse(parse_results(payload,'now')[0]['completed'])
 def test_scorers_exclude_passing_and_combine_direct_touchdowns(self):
  from scripts.refresh_public_game_odds import parse_scorers
  athlete={'id':'one','displayName':'Player One'}
  groups=[{'name':name,'keys':[key],'athletes':[{'athlete':athlete,'stats':[value]}]} for name,key,value in [('passing','passingTouchdowns','4'),('rushing','rushingTouchdowns','1'),('receiving','receivingTouchdowns','2')]]
  rows=parse_scorers({'boxscore':{'players':[{'team':{'displayName':'Team A'},'statistics':groups}]}})
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['touchdowns'],3)
 def test_complete_scoring_requires_both_teams_valid_rushing_and_receiving_boxes(self):
  from scripts.refresh_public_game_odds import scorers_complete
  groups=[{'name':kind,'keys':[key],'athletes':[{'stats':['0']}]} for kind,key in [('rushing','rushingTouchdowns'),('receiving','receivingTouchdowns')]]
  payload={'boxscore':{'players':[{'statistics':groups},{'statistics':groups}]}}
  self.assertTrue(scorers_complete(payload));groups[0]['athletes'][0]['stats']=['-'];self.assertFalse(scorers_complete(payload))
