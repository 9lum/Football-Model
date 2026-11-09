import unittest
from types import SimpleNamespace
import pandas as pd
from edge.receiving_routes import RouteContext,summarize,target_records
class RouteContextTests(unittest.TestCase):
 def fixture(self):
  rows=[]
  for season,club,pid,games,n,yards,epa in [(2025,'L','league',3,60,10,.1),(2026,'C','p',3,7,12,.2),(2026,'B','other',3,40,16,.8)]:
   for w in range(1,games+1):
    for i in range(n):rows.append({'season':season,'game_id':f'{season}_{club}_{w}','receiver_player_id':pid,'team':'A','opponent':club,'kickoff':pd.Timestamp(f'{season}-09-01',tz='UTC')+pd.Timedelta(days=w*7),'depth':'short','pass_location':'left','region':'short_left','air_yards':5.,'yards_gained':yards,'epa':epa,'complete_pass':1,'coverage':'zone'})
  return pd.DataFrame(rows)
 def test_only_prior_games_contribute_to_depth_overlap_and_profile_shares(self):
  records=self.fixture();row=SimpleNamespace(player_id='p',opponent_team='B',kickoff=pd.Timestamp('2026-09-30',tz='UTC'),matchup_man_rate=.3,matchup_zone_rate=.7)
  context=RouteContext(records,2026).context(row);self.assertEqual(context['status'],'available');self.assertEqual(context['direction'],1);self.assertEqual(context['profile']['depthShares']['short'],1);self.assertEqual(sum(z['targetShare'] for z in context['profile']['zones']),1)
  future=records[records.opponent.eq('B')].copy();future['kickoff']=pd.Timestamp('2026-10-01',tz='UTC');future['epa']=-100;future['yards_gained']=0
  changed=RouteContext(pd.concat([records,future]),2026).context(row);self.assertEqual(context['signal'],changed['signal']);self.assertFalse(context['routeTypesAvailable'])
 def test_missing_data_keeps_the_baseline(self):
  engine=RouteContext(pd.DataFrame(),2026);row=SimpleNamespace(player_id='missing',opponent_team='B',kickoff=pd.Timestamp('2026-10-01',tz='UTC'))
  self.assertEqual(engine.context(row)['status'],'unavailable');self.assertEqual(engine.context(row)['signal'],0)

class BehindLineTests(unittest.TestCase):
 def test_negative_air_yards_are_separate_from_short_and_catch_share_uses_catches(self):
  rows=pd.DataFrame([{'season':2026,'game_id':'g','kickoff':pd.Timestamp('2026-11-01',tz='UTC'),'depth':'short','air_yards':air,'pass_location':'left','complete_pass':caught,'yards_gained':yards,'epa':0.} for air,caught,yards in [(-3,1,7),(-1,0,0),(0,1,4),(8,1,9)]])
  s=summarize(rows,'test');self.assertEqual(s['depthDefinitionVersion'],2);self.assertEqual(s['behindLineTargets'],2);self.assertEqual(s['behindLineReceptions'],1);self.assertEqual(s['behindLineYards'],7);self.assertAlmostEqual(s['behindLineCatchShare'],1/3);self.assertEqual(s['depthShares']['behind'],.5);self.assertEqual(s['depthShares']['short'],.5);self.assertEqual(len(s['zones']),12);self.assertAlmostEqual(sum(v['targetShare'] for v in s['zones']),1)
