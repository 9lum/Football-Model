import unittest
import pandas as pd
from edge.passing_profiles import quarterback_records,passing_summary
class QuarterbackProfileTests(unittest.TestCase):
 def fixture(self):
  common={'game_id':'g','season':2026,'season_type':'REG','passer_player_id':'qb','rusher_player_id':None,'pass_attempt':1,'rush_attempt':0,'qb_dropback':1,'qb_scramble':0,'qb_kneel':0,'qb_spike':0,'sack':0,'no_play':0,'air_yards':5,'pass_location':'left','complete_pass':1,'yards_gained':8,'epa':.2,'cpoe':4}
  changes=[{}, {'air_yards':15,'pass_location':'middle','complete_pass':0,'yards_gained':0}, {'air_yards':25,'pass_location':'right','yards_gained':30}, {'pass_location':None,'complete_pass':0,'yards_gained':0}, {'sack':1,'pass_attempt':0,'air_yards':None,'yards_gained':-7}, {'pass_attempt':0,'rush_attempt':1,'qb_scramble':1,'rusher_player_id':'qb','air_yards':None,'yards_gained':12}, {'passer_player_id':None,'rusher_player_id':'qb','qb_dropback':0,'pass_attempt':0,'rush_attempt':1,'air_yards':None,'yards_gained':4}, {'qb_kneel':1,'pass_attempt':0,'rush_attempt':1,'qb_dropback':0,'rusher_player_id':'qb'}, {'qb_spike':1}, {'no_play':1}, {'game_id':'future'}]
  plays=pd.DataFrame([{**common,**c,'play_id':i} for i,c in enumerate(changes)])
  schedules=pd.DataFrame([{'game_id':'g','completed':True,'kickoff':pd.Timestamp('2026-10-01',tz='UTC')},{'game_id':'future','completed':True,'kickoff':pd.Timestamp('2026-11-20',tz='UTC')}])
  return quarterback_records(plays,schedules,pd.Timestamp('2026-11-09',tz='UTC'))
 def test_throw_locations_and_run_denominators_exclude_sacks_spikes_and_kneels(self):
  records=self.fixture();self.assertEqual(len(records),7);self.assertEqual(set(records.playerId),{'qb'})
  s=passing_summary(records,'test');self.assertEqual(s['throwAttempts'],4);self.assertEqual(s['locatedAttempts'],3);self.assertEqual(s['dropbacks'],6);self.assertEqual(s['scrambles'],1);self.assertAlmostEqual(s['scrambleRate'],1/6);self.assertEqual(s['designedRushAttempts'],1);self.assertEqual(s['scrambleYards'],12);self.assertEqual(s['designedRushYards'],4);self.assertEqual(s['designedRushShare'],.5);self.assertAlmostEqual(sum(z['targetShare'] for z in s['zones']),1);self.assertEqual(s['completionRate'],.5)
 def test_missing_run_classification_is_unknown_not_an_invented_designed_carry(self):
  records=self.fixture();records.loc[records.rush_attempt.eq(1),'qb_scramble']=float('nan');s=passing_summary(records,'test');self.assertIsNone(s['scrambleRate']);self.assertIsNone(s['designedRushAttempts'])
 def test_rushing_evidence_survives_no_located_throws(self):
  records=self.fixture();records['pass_location']=None;s=passing_summary(records,'test');self.assertEqual(s['status'],'unavailable');self.assertEqual(s['scrambles'],1);self.assertEqual(s['dropbacks'],6)
 def test_empty_is_explicitly_unavailable(self):
  self.assertEqual(passing_summary(pd.DataFrame(),'test')['status'],'unavailable')
