import unittest
import pandas as pd
from edge.chemistry import build_context,starter_games

class ChemistryTests(unittest.TestCase):
 def data(self):
  games=[];stats=[]
  for i in range(1,13):
   qb='kirk' if i<=6 else 'other';year=2023 if i<=6 else 2026
   games.append(dict(season=year,week=i,game_type='REG',gameday=f'{year}-09-{i:02}',home_team='MIN',away_team='GB',home_qb_id=qb,away_qb_id='gb',home_score=20,away_score=10))
   stats.extend([dict(season=year,week=i,team='MIN',position='QB',player_id=qb,attempts=30),dict(season=year,week=i,team='MIN',position='WR',player_id='jj',targets=10 if qb=='kirk' else 7,receptions=7 if qb=='kirk' else 4,receiving_yards=100 if qb=='kirk' else 50,receiving_tds=.4)])
  return pd.DataFrame(stats),pd.DataFrame(games)
 def test_old_pair_is_positive_but_shrunk(self):
  stats,games=self.data();r=build_context(stats,games,[dict(playerId='jj',team='MIN',position='WR'),dict(playerId='kirk',name='Kirk',team='MIN',position='QB',fresh=True,expectedStarter=True)],pd.Timestamp('2026-11-12',tz='UTC'))['players']['jj']
  self.assertEqual(r['withQB']['games'],6);self.assertTrue(1<r['factors']['player_reception_yds']<=1.15);self.assertLess(r['confidence'],.25)
 def test_relief_and_future_games_excluded(self):
  stats,games=self.data();stats.loc[stats.player_id.eq('kirk'),'attempts']=8
  self.assertFalse(starter_games(games,stats,pd.Timestamp('2026-11-12',tz='UTC')).qbId.eq('kirk').any())
  self.assertTrue(starter_games(games,stats,pd.Timestamp('2020-01-01',tz='UTC')).empty)
 def test_no_shared_sample_no_invented_boost(self):
  stats,games=self.data();r=build_context(stats,games,[dict(playerId='jj',team='MIN',position='WR'),dict(playerId='new',name='New QB',team='MIN',position='QB',fresh=True,expectedStarter=True)],pd.Timestamp('2026-11-12',tz='UTC'))
  self.assertEqual(r['players'],{})

class IdentityTests(unittest.TestCase):
 def test_mislabeled_gsis_row_is_removed_without_merging_real_players(self):
  from edge.availability import verified_depth
  people=pd.DataFrame([{'gsis_id':'a','display_name':'Tyler Conklin'},{'gsis_id':'b','display_name':'Ryan Izzo'}])
  good={'playerId':'a','name':'Tyler Conklin'};bad={'playerId':'b','name':'Tyler Conklin'}
  valid,rejected=verified_depth([good,bad],people)
  self.assertEqual(valid,[good]);self.assertEqual(rejected,[bad])

 def test_known_nicknames_do_not_drop_legitimate_depth_rows(self):
  from edge.availability import verified_depth
  people=pd.DataFrame([{'gsis_id':'a','display_name':'Marquise Brown'}]);row={'playerId':'a','name':'Hollywood Brown'}
  self.assertEqual(verified_depth([row],people),([row],[]))
