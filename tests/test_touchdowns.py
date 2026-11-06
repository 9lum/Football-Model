import unittest
import numpy as np
import pandas as pd
from edge.touchdowns import scoring_opportunities,build_frame,FEATURES,attd_price,matched_quotes,american
class TouchdownTests(unittest.TestCase):
 def plays(self):
  rows=[]
  for year in [2025,2026]:
   for week in range(1,6):
    for pid,kind in [('wr','pass'),('qb','run')]:
     rows.append(dict(game_id=f'{year}_{week}',play_id=1,season=year,season_type='REG',week=week,posteam='A',defteam='B',play_type=kind,yardline_100=4,rusher_player_id=pid if kind=='run' else None,receiver_player_id=pid if kind=='pass' else None,rush_attempt=int(kind=='run'),pass_attempt=int(kind=='pass'),qb_dropback=int(kind=='pass'),qb_kneel=0,qb_spike=0,rush_touchdown=int(kind=='run'),pass_touchdown=int(kind=='pass' and week%2==0),epa=1.,complete_pass=int(week%2==0)))
  return pd.DataFrame(rows)
 def test_quarterback_passing_touchdowns_are_not_scoring_opportunities(self):
  o,_=scoring_opportunities(self.plays(),{'wr':'WR','qb':'QB'},2026);q=o[o.player_id.eq('qb')];self.assertTrue(q.kind.eq('rush').all());self.assertEqual(q.targets.sum(),0);self.assertEqual(o[o.player_id.eq('wr')].rzTargets.sum(),10);self.assertEqual(o[o.player_id.eq('wr')].rzTouches.sum(),4)
 def test_current_season_td_outcomes_do_not_change_preseason_expected_td_calibration(self):
  p=self.plays();a,_=scoring_opportunities(p,{'wr':'WR','qb':'QB'},2026);p.loc[p.season.eq(2026),['rush_touchdown','pass_touchdown']]=0;b,_=scoring_opportunities(p,{'wr':'WR','qb':'QB'},2026);np.testing.assert_array_equal(a.xTD.to_numpy(),b.xTD.to_numpy())
 def test_yes_no_semantics_and_price_matching(self):
  self.assertEqual(attd_price({'name':'Yes','description':'Player'}),'Player');self.assertIsNone(attd_price({'name':'No','description':'Player'}));self.assertEqual(american(.5),-100)
  from types import SimpleNamespace
  g=SimpleNamespace(home_team='SEA',away_team='SF',kickoff=pd.Timestamp('2026-11-08T18:00Z'));event={'home_team':'Seattle Seahawks','away_team':'San Francisco 49ers','commence_time':g.kickoff.isoformat(),'bookmakers':[{'title':'Test','markets':[{'key':'player_anytime_td','last_update':'2026-11-06T18:00Z','outcomes':[{'name':'Yes','description':'Player','price':200},{'name':'No','description':'Player','price':-250}]}]}]};r=matched_quotes({'name':'Player'},g,{'data':[event]},pd.Timestamp('2026-11-06T18:01Z'),.4,{'validationPassed':True,'calibrationGap':.05},{'confirmed':True,'observedAt':'2026-11-06T17:00Z'});self.assertEqual(len(r),1);self.assertAlmostEqual(r[0]['estimatedReturn'],.2);self.assertFalse(r[0]['qualified']);self.assertIn('estimated win probability below 70%',r[0]['flags'])
 def test_game_and_future_statistics_do_not_leak_into_player_features(self):
  plays=self.plays();o,d=scoring_opportunities(plays,{'wr':'WR','qb':'QB'},2026);stats=[];schedule=[]
  for year in [2025,2026]:
   for week in range(1,6):
    kickoff=pd.Timestamp(f'{year}-09-01',tz='UTC')+pd.Timedelta(days=week*7)
    for club,opp in [('A','B'),('B','A')]:schedule.append(dict(game_id=f'{year}_{week}',season=year,week=week,team=club,opponent_team=opp,kickoff=kickoff,completed=True,home=int(club=='A'),home_team='A',away_team='B'))
    for pid,pos in [('wr','WR'),('qb','QB')]:stats.append(dict(player_id=pid,player_display_name=pid,position=pos,team='A',season=year,week=week,rushing_tds=1 if pid=='qb' else 0,receiving_tds=int(week%2==0) if pid=='wr' else 0))
  s=pd.DataFrame(stats);sch=pd.DataFrame(schedule);a,_=build_frame(s,sch,o,d,pd.Timestamp('2027-01-01',tz='UTC'));cutoff=sch[sch.game_id.eq('2026_4')].kickoff.iloc[0];changed=o.copy();changed.loc[changed.season.eq(2026)&changed.week.ge(4),['xTD','td','rzTouches']]=999;b,_=build_frame(s,sch,changed,d,pd.Timestamp('2027-01-01',tz='UTC'));mask=a.kickoff.le(cutoff);pd.testing.assert_frame_equal(a.loc[mask,FEATURES].reset_index(drop=True),b.loc[mask,FEATURES].reset_index(drop=True))
