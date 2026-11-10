import unittest
import pandas as pd
from scripts.refresh_position_rankings import build

class PositionRankingTests(unittest.TestCase):
 def stats(self):
  keys='passing_epa rushing_epa receiving_epa passing_yards rushing_yards receiving_yards sack_yards_lost attempts sacks_suffered carries targets passing_interceptions sack_fumbles_lost rushing_fumbles_lost rushing_tds receiving_tds def_sacks def_tackles_for_loss def_qb_hits def_pass_defended def_tackles_solo def_fumbles_forced def_interceptions'.split();rows=[]
  for club in ['ARI','ATL']:
   for pos in ['QB','RB','WR','TE','DE','LB','CB','SAF']:
    row=dict.fromkeys(keys,0.);row.update(player_id=club+pos,game_id='2026_01_ARI_ATL',season=2026,week=1,season_type='REG',team=club,position=pos)
    if pos=='QB':row.update(attempts=30,sacks_suffered=1 if club=='ARI' else 5,passing_epa=20 if club=='ARI' else -10,passing_yards=300,sack_yards_lost=-7)
    if pos=='RB':row.update(carries=20,targets=5,rushing_epa=5,rushing_yards=100,receiving_yards=30)
    if pos in ['WR','TE']:row.update(targets=10,receiving_yards=100,receiving_epa=5)
    rows.append(row)
  return pd.DataFrame(rows)
 def test_efficiency_and_negative_sack_rate_direction(self):
  rows={r['team']:r for r in build(self.stats(),2026)}
  self.assertLess(rows['ARI']['units']['QB']['rank'],rows['ATL']['units']['QB']['rank'])
  self.assertLess(rows['ARI']['units']['OL']['rank'],rows['ATL']['units']['OL']['rank'])
  self.assertIsNone(rows['BUF']['units']['QB']['rank'])
 def test_team_games_do_not_count_individual_appearances(self):
  d=self.stats();extra=d[(d.team=='ARI')&(d.position=='WR')].copy();extra['player_id']='slot-wr';d=pd.concat([d,extra]);ari=next(r for r in build(d,2026) if r['team']=='ARI');self.assertEqual(ari['games'],1);self.assertEqual(ari['units']['WR']['metrics']['yardsPerGame'],200)
 def test_duplicate_statistics_are_rejected(self):
  d=self.stats()
  with self.assertRaises(ValueError):build(pd.concat([d,d.iloc[:1]]),2026)

if __name__=='__main__':unittest.main()
