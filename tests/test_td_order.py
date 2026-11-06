import unittest
import numpy as np,pandas as pd
from edge.td_order import attach_labels,coherent,residual_budget
class ScorerOrderTests(unittest.TestCase):
 def test_defensive_first_td_is_not_reassigned_to_the_next_offensive_scorer(self):
  plays=pd.DataFrame([{'game_id':'g','play_id':1,'touchdown':1,'td_player_id':'defender'},{'game_id':'g','play_id':2,'touchdown':1,'td_player_id':'receiver'}]);frame=pd.DataFrame([{'game_id':'g','player_id':'receiver','kickoff':pd.Timestamp('2026-09-01',tz='UTC'),'forecast':False}]);d=attach_labels(frame,plays);self.assertEqual(d.iloc[0].actualFirstTD,0);self.assertEqual(d.iloc[0].actualLastTD,1)
 def test_scorer_order_history_is_shifted_and_future_labels_do_not_change_it(self):
  frame=pd.DataFrame([{'game_id':'g'+str(i),'player_id':'p','kickoff':pd.Timestamp('2026-09-01',tz='UTC')+pd.Timedelta(days=i),'forecast':False} for i in range(4)]);plays=pd.DataFrame([{'game_id':'g'+str(i),'play_id':1,'touchdown':1,'td_player_id':'p'} for i in range(4)]);a=attach_labels(frame,plays);plays.loc[plays.game_id.isin(['g2','g3']),'td_player_id']='other';b=attach_labels(frame,plays);np.testing.assert_array_equal(a.firstTD_last6.iloc[:3],b.firstTD_last6.iloc[:3])
 def test_mutually_exclusive_probabilities_reserve_unmodeled_mass_and_cannot_exceed_attd(self):
  result=coherent([.8,.7,.4],[.5,.6,.3],['g','g','other'],.8);self.assertLessEqual(result[:2].sum(),.8);self.assertTrue((result<=np.array([.5,.6,.3])).all());self.assertAlmostEqual(result[2],.3)
 def test_nullified_touchdown_does_not_win_first_scorer(self):
  plays=pd.DataFrame([{'game_id':'g','play_id':1,'touchdown':1,'td_player_id':'other','play_type':'no_play'},{'game_id':'g','play_id':2,'touchdown':1,'td_player_id':'p','play_type':'pass'}]);frame=pd.DataFrame([{'game_id':'g','player_id':'p','kickoff':pd.Timestamp('2026-09-01',tz='UTC'),'forecast':False}]);d=attach_labels(frame,plays);self.assertEqual(d.iloc[0].actualFirstTD,1)
