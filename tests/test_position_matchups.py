import unittest
import pandas as pd
import numpy as np
from edge.position_matchups import attach_position_matchups,METRICS

class PositionMatchups(unittest.TestCase):
    def fixture(self):
        rows=[]
        for week in range(1,9):
            for pos,yards in [('WR',100+week),('TE',20+week)]:
                rows.append(dict(game_id='g'+str(week),season=2026,team='A',opponent_team='B',kickoff=pd.Timestamp('2026-09-01',tz='UTC')+pd.Timedelta(days=7*week),position=pos,forecast=False,**{k:0. for k in METRICS},**{}))
                rows[-1].update(receiving_yards=yards,targets=10.,receptions=5.,receiving_tds=1.)
        return pd.DataFrame(rows)
    def test_position_specific_and_future_outcomes_do_not_leak(self):
        d=self.fixture();a,_=attach_position_matchups(d,[],pd.DataFrame());self.assertTrue(np.isnan(a.iloc[0].opp_position_receiving_yards_last6))
        # Query defense B at week 4 from another offense; WR and TE remain distinct.
        q=d[d.game_id.eq('g4')].copy();q['team']='C';q['forecast']=True;q['game_id']='future';query=pd.concat([d,q],ignore_index=True)
        a,features=attach_position_matchups(query,[],pd.DataFrame());future=a[a.forecast]
        self.assertAlmostEqual(future[future.position.eq('WR')].iloc[0].opp_position_receiving_yards_last6,102.)
        self.assertAlmostEqual(future[future.position.eq('TE')].iloc[0].opp_position_receiving_yards_last6,22.)
        query.loc[query.kickoff>=q.kickoff.iloc[0],'receiving_yards']=99999
        b,_=attach_position_matchups(query,[],pd.DataFrame());pd.testing.assert_frame_equal(future[features].reset_index(drop=True),b[b.forecast][features].reset_index(drop=True))
    def test_offense_strength_and_zero_position_games(self):
        d=self.fixture();q=d[d.game_id.eq('g8')].copy();q['team']='C';q['forecast']=True;q['game_id']='future'
        a,_=attach_position_matchups(pd.concat([d,q],ignore_index=True),[],pd.DataFrame());wr=a[a.forecast&a.position.eq('WR')].iloc[0]
        self.assertGreater(wr.opp_position_receiving_yards_offense_adjusted_delta6,0)
        self.assertAlmostEqual(wr.opp_position_catch_rate_last6,.5)
        self.assertAlmostEqual(wr.opp_position_td_points_last6,6.)
        q=q.iloc[:1].copy();q['position']='RB';a,_=attach_position_matchups(pd.concat([d,q]),[],pd.DataFrame());rb=a[a.forecast].iloc[0];self.assertEqual(rb.opp_position_receiving_yards_last6,0);self.assertEqual(rb.opp_position_games_last6,6)

    def test_score_allowance_excludes_current_and_future_scores(self):
        d=self.fixture();q=d[d.game_id.eq('g4')].iloc[:1].copy();q['team']='C';q['forecast']=True;q['game_id']='future'
        schedule=d[['game_id','team']].drop_duplicates();schedule['points_allowed']=20.
        a,_=attach_position_matchups(pd.concat([d,q]),[],schedule)
        schedule.loc[schedule.game_id.isin(['g4','g5','g6','g7','g8']),'points_allowed']=999.
        b,_=attach_position_matchups(pd.concat([d,q]),[],schedule)
        self.assertEqual(a[a.forecast].iloc[0].opp_position_points_allowed_last6,20)
        self.assertEqual(b[b.forecast].iloc[0].opp_position_points_allowed_last6,20)
