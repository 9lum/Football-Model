import unittest
import pandas as pd
from scripts.refresh_route_experiment import aggregate

class RouteExperimentTests(unittest.TestCase):
 def sample(self):
  return pd.DataFrame([dict(game_id='2025_01_A_B',play_id=i,season=2025,season_type='REG',week=1,game_date='2025-09-07',receiver_player_id='r',passer_player_id='q',pass_attempt=1,play_type='pass',complete_pass=1,yards_gained=10,air_yards=5,epa=.2) for i in range(1,5)])
 def test_charted_target_denominator_and_passer_identity(self):
  p=self.sample();part=pd.DataFrame([dict(nflverse_game_id='2025_01_A_B',play_id=i,route=route) for i,route in [(1,'QUICK OUT'),(2,'DEEP OUT'),(3,'GO')]])
  out=aggregate(p,part);r=out['r']['season'];self.assertEqual(r['chartedTargets'],3);self.assertEqual(r['coverage'],.75);self.assertAlmostEqual(sum(x['share'] for x in r['routes']),1);self.assertEqual(next(x for x in r['routes'] if x['key']=='out')['targets'],2);self.assertEqual(out['q']['kind'],'passing');self.assertEqual(out['q']['season']['chartedTargets'],3)
 def test_same_play_number_from_other_game_cannot_join_and_no_play_excluded(self):
  p=self.sample();p.loc[0,'play_type']='no_play';part=pd.DataFrame([dict(nflverse_game_id='2025_01_A_B',play_id=1,route='GO'),dict(nflverse_game_id='other-game',play_id=2,route='POST')]);self.assertEqual(aggregate(p,part),{})
 def test_conflicting_charting_is_rejected(self):
  part=pd.DataFrame([dict(nflverse_game_id='2025_01_A_B',play_id=1,route=r) for r in ['GO','POST']])
  with self.assertRaises(ValueError):aggregate(self.sample(),part)
 def test_trick_play_passing_never_replaces_receiving_sample(self):
  p=self.sample();p.loc[3,'passer_player_id']='r';p.loc[3,'receiver_player_id']='q'
  part=pd.DataFrame([dict(nflverse_game_id='2025_01_A_B',play_id=i,route='GO') for i in range(1,5)])
  out=aggregate(p,part)
  self.assertEqual(out['r']['season']['chartedTargets'],3)
  self.assertEqual(out['r']['passingProfile']['season']['chartedTargets'],1)
  self.assertEqual(out['q']['passingProfile']['season']['chartedTargets'],3)

if __name__=='__main__':unittest.main()
