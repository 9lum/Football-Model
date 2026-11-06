import unittest
import pandas as pd
from edge.game_model import build_rows,fair
class GameModelTests(unittest.TestCase):
 def test_target_and_future_scores_do_not_enter_features(self):
  games=[]
  for week in range(1,8):games.append({'game_id':f'2026_{week}_SEA_SF','season':2026,'week':week,'game_type':'REG','gameday':f'2026-10-{week:02d}','gametime':'13:00','home_team':'SEA','away_team':'SF','home_score':20+week,'away_score':14+week,'home_rest':7,'away_rest':7})
  schedule=pd.DataFrame(games);a,features=build_rows(schedule,pd.DataFrame(),now='2026-11-06T00:00:00Z');changed=schedule.copy();changed.loc[changed.week.ge(5),'home_score']=100;b,_=build_rows(changed,pd.DataFrame(),now='2026-11-06T00:00:00Z');pd.testing.assert_frame_equal(a[a.week.eq(5)][features].reset_index(drop=True),b[b.week.eq(5)][features].reset_index(drop=True));self.assertNotEqual(a[a.week.eq(6)].home_points_for_last3.iloc[0],b[b.week.eq(6)].home_points_for_last3.iloc[0]);self.assertTrue(all('spread_line' not in f for f in features))
 def test_moneyline_conditions_on_tie_push(self):self.assertEqual(fair(.45,.1),-100);self.assertIsNone(fair(1,0))
