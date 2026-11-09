import unittest
import numpy as np
import pandas as pd
from edge.availability import parse_sleeper,parse_espn,match_and_resolve,roster_roles,qb_scenarios
from edge.replacement_forecasts import qb_forecast
class ReplacementForecastTests(unittest.TestCase):
 def test_current_provider_out_excludes_without_claiming_official_confirmation(self):
  now=pd.Timestamp('2026-11-09T18:00Z');payload={'season':{'year':2026},'injuries':[{'abbreviation':'MIN','injuries':[{'athlete':{'displayName':'Test QB','position':{'abbreviation':'QB'}},'status':'Out','date':'2026-11-07T18:00Z'}]}]}
  rows=parse_espn(payload,2026,9,now.isoformat());result,_=match_and_resolve(rows,[],[{'playerId':'s','name':'Test QB','team':'MIN'}],2026,9,now)
  self.assertTrue(result['s']['ruledOut']);self.assertFalse(result['s']['confirmed']);self.assertEqual(result['s']['confirmationLevel'],'provider')
  payload['season']['year']=2025;rows=parse_espn(payload,2026,9,now.isoformat());wrong,_=match_and_resolve(rows,[],[{'playerId':'s','name':'Test QB','team':'MIN'}],2026,9,now);self.assertFalse(wrong['s']['ruledOut'])
 def test_sleeper_state_scope_ids_and_no_active_roster_equals_cleared_assumption(self):
  state={'season':'2026','season_type':'regular','week':9};players={'1':{'full_name':'Starter','gsis_id':' 00-1','team':'MIN','position':'QB','depth_chart_order':2,'injury_status':'Out','status':'Active'},'2':{'full_name':'Backup','gsis_id':'00-2','team':'MIN','position':'QB','depth_chart_order':1,'injury_status':None,'status':'Active'}}
  rows,depth=parse_sleeper(players,state,[],2026,9,'2026-11-09T18:00Z');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['playerId'],'00-1');self.assertEqual(depth[0]['playerId'],'00-1')
  with self.assertRaises(ValueError):parse_sleeper(players,state,[],2026,10,'2026-11-09T18:00Z')
 def test_next_available_backup_and_doubtful_are_distinct_from_questionable(self):
  depth=[{'playerId':pid,'name':pid,'team':'MIN','position':'QB','slot':0,'rank':rank,'fresh':True} for rank,pid in enumerate(['s','b','c'],1)]
  roles=roster_roles(depth,{'s':{'ruledOut':True},'b':{'ruledOut':True}});self.assertTrue(roles[2]['expectedStarter']);self.assertFalse(roles[0]['expectedStarter'])
  roles=roster_roles(depth,{'s':{'status':'DOUBTFUL','ruledOut':False}});self.assertTrue(roles[1]['conditionalStarter']);self.assertFalse(roles[0]['health']['ruledOut'])
  roles=roster_roles(depth,{'s':{'status':'QUESTIONABLE','ruledOut':False}});self.assertTrue(roles[0]['expectedStarter']);self.assertFalse(roles[1]['replacement'])
 def test_backup_qb_has_consistent_full_passing_counts_and_own_rushing_profile(self):
  reference={'playerId':'s','team':'MIN','opponent':'BUF','homeTeam':'MIN','awayTeam':'BUF','gameId':'2026_09_BUF_MIN','kickoff':'2026-11-10T01:15Z','features':{'attempts_last3':40,'carries_last3':9},'marketSamples':{'player_pass_attempts':{'values':[40]*32},'player_pass_yds':{'values':[260]*32},'player_rush_yds':{'values':[65]*32}}};role={'playerId':'b','name':'Backup','position':'QB'};info={'recordedStarts':100,'recentStarts':[{'attempts':30,'completions':19,'passing_tds':1,'passing_interceptions':1,'carries':2,'rushing_yards':6,'rushing_tds':0}]*3}
  f=qb_forecast(reference,role,{'backupPassingYards':200},info);m=f['marketSamples'];self.assertEqual(len(m),8);self.assertAlmostEqual(m['player_pass_yds']['mean'],200);self.assertEqual(m['player_rush_yds']['mean'],6);self.assertEqual(m['player_rush_attempts']['mean'],2)
  for a,c,t,i in zip(m['player_pass_attempts']['values'],m['player_pass_completions']['values'],m['player_pass_tds']['values'],m['player_pass_interceptions']['values']):self.assertLessEqual(c,a);self.assertLessEqual(t,c);self.assertLessEqual(i,a-c)
  self.assertTrue(all(not v['validationPassed'] for v in m.values()));self.assertEqual(reference['marketSamples']['player_rush_yds']['values'][0],65)
  f=qb_forecast(reference,role,{'backupPassingYards':200},{'recordedStarts':0});self.assertNotIn('player_rush_yds',f['marketSamples'])
