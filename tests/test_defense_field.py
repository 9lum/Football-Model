import unittest
import numpy as np
import pandas as pd
from edge.defense_field import build,summarize
class DefenseFieldTests(unittest.TestCase):
 def sample(self):
  rows=[]
  for i,air,side,caught in [(1,-2,'left',1),(2,5,'left',0),(3,20,'middle',1),(4,6,'left',0),(5,np.nan,'right',1)]:rows.append(dict(game_id='g1',play_id=i,season=2026,season_type='REG',defteam='LA',pass_attempt=1,no_play=0,complete_pass=caught,air_yards=air,pass_location=side,yards_gained=7 if air<0 else 25 if caught else 0,epa=.2,kickoff=pd.Timestamp('2026-09-14',tz='UTC')))
  return pd.DataFrame(rows)
 def test_completion_denominator_is_not_target_share(self):
  s=summarize(self.sample());behind=next(z for z in s['zones'] if z['depth']=='behind' and z['area']=='left');self.assertEqual(s['completions'],2);self.assertEqual(s['totalCompletions'],3);self.assertEqual(s['unlocatedCompletions'],1);self.assertEqual(behind['completionShare'],.5);self.assertEqual(behind['targetShare'],.25);self.assertAlmostEqual(sum(z['completionShare'] for z in s['zones']),1);self.assertEqual(s['behindLineCompletions'],1);self.assertEqual(len(s['zones']),12)
 def test_zero_completion_denominator_and_unknown_outcomes_are_not_fabricated(self):
  d=self.sample();d['complete_pass']=0;s=summarize(d);self.assertEqual(s['completions'],0);self.assertTrue(all(z['completionShare'] is None for z in s['zones']));d.loc[0,'complete_pass']=np.nan;s=summarize(d);self.assertEqual(s['unknownOutcomePasses'],1)
 def test_completed_regular_season_only_with_team_alias_and_no_play(self):
  d=self.sample().drop(columns='kickoff');future=d.iloc[:1].copy();future['game_id']='g2';post=d.iloc[:1].copy();post['game_id']='g3';post['season_type']='POST';null=d.iloc[:1].copy();null['play_id']=99;null['defteam']=None;d.loc[d.play_id==1,'no_play']=1;d=pd.concat([d,future,post,null],ignore_index=True)
  schedule=pd.DataFrame([dict(game_id='g1',kickoff=pd.Timestamp('2026-09-14',tz='UTC'),completed=True),dict(game_id='g2',kickoff=pd.Timestamp('2026-09-21',tz='UTC'),completed=False),dict(game_id='g3',kickoff=pd.Timestamp('2026-09-15',tz='UTC'),completed=True)])
  x=build(d,schedule,2026,pd.Timestamp('2026-09-22',tz='UTC'));self.assertEqual(list(x),['LAR']);self.assertEqual(x['LAR']['season']['games'],1);self.assertEqual(x['LAR']['season']['completions'],1);self.assertEqual(x['LAR']['season']['behindLineCompletions'],0)
 def test_two_point_attempts_and_spikes_are_excluded(self):
  d=self.sample();d['two_point_attempt']=0;d['qb_spike']=0;two=d.iloc[:1].copy();two['play_id']=6;two['two_point_attempt']=1;spike=d.iloc[:1].copy();spike['play_id']=7;spike['qb_spike']=1
  s=summarize(pd.concat([d,two,spike]));self.assertEqual(s['totalCompletions'],3);self.assertEqual(s['completions'],2)
 def test_duplicate_play_is_rejected(self):
  d=self.sample().drop(columns='kickoff');s=pd.DataFrame(columns=['game_id','kickoff','completed'])
  with self.assertRaises(ValueError):build(pd.concat([d,d.iloc[:1]]),s,2026,pd.Timestamp.now(tz='UTC'))
if __name__=='__main__':unittest.main()
