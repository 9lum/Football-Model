import unittest
import numpy as np
import pandas as pd
from edge.features import prepare
from edge.model import DistributionForest,crps,walk_forward
from edge.markets import probability,price,decimal,scan
from edge.data import normalize_stats,add_snap_zeros,schedule_rows
from edge.routes import match_snapshot


def fixture():
    stats=[];schedule=[]
    for year in [2025,2026]:
        for week in range(1,9):
            date=pd.Timestamp(f'{year}-09-01',tz='UTC')+pd.Timedelta(days=7*(week-1))
            for home,team,opp in [(1,'SEA','SF'),(0,'SF','SEA')]:
                schedule.append(dict(game_id=f'{year}_{week}_SEA_SF',season=year,week=week,team=team,opponent_team=opp,kickoff=date,home=home,home_team='SEA',away_team='SF',completed=True))
                for i in range(4):
                    stats.append(dict(player_id=team+str(i),player_display_name=team+' Player '+str(i),position='WR',team=team,season=year,week=week,targets=i+week%3,receptions=i,receiving_yards=i*10+week,receiving_air_yards=20+i,receiving_yards_after_catch=5+i,offense_snaps=40,offense_pct=.7))
    return pd.DataFrame(stats),pd.DataFrame(schedule)

class EngineTests(unittest.TestCase):
    def test_target_game_and_future_outcomes_do_not_change_features(self):
        stats,sched=fixture();a,features=prepare(stats,sched,now='2027-01-01T00:00:00Z')
        changed=stats.copy();changed.loc[(changed.season==2026)&(changed.week>=5),'receiving_yards']=9999
        b,_=prepare(changed,sched,now='2027-01-01T00:00:00Z')
        select=(a.season==2026)&(a.week==5)
        pd.testing.assert_frame_equal(a.loc[select,features].reset_index(drop=True),b.loc[select,features].reset_index(drop=True))
        self.assertNotEqual(a.loc[(a.season==2026)&(a.week==6),'receiving_yards_last3'].iloc[0],b.loc[(b.season==2026)&(b.week==6),'receiving_yards_last3'].iloc[0])
    def test_fit_sampling_and_probability_partitions(self):
        x=pd.DataFrame({'x':np.arange(120),'missing':np.nan});y=np.column_stack([np.arange(120),np.arange(120)%9])
        f=DistributionForest(trees=8,min_leaf=5).fit(x,y);s=f.sample(x.iloc[:2],draws=64)
        self.assertEqual(s.shape,(2,64,2));self.assertTrue(np.array_equal(s,f.sample(x.iloc[:2],64)))
        w,p,l=probability(s[0],30,'Over',0);self.assertAlmostEqual(w+p+l,1)
        self.assertEqual(price(.5,0,-100),0);self.assertEqual(decimal(150),2.5)
    def test_crps_deterministic_boundary(self):
        self.assertEqual(crps(np.zeros((3,10)),np.zeros(3)),0)
        self.assertEqual(crps(np.zeros((3,10)),np.ones(3)),1)
    def test_current_season_walk_forward_has_separate_final_week(self):
        stats,sched=fixture();frame,features=prepare(stats,sched,now='2027-01-01T00:00:00Z')
        r=walk_forward(frame,features,2026,trees=4,min_train=20)
        self.assertEqual(r['latestWeekHoldout']['week'],8)
        self.assertEqual(r['folds'][0]['trainRows'],40)
        self.assertFalse(r['configurationTunedOnLatestWeek']);self.assertIsNone(r['roi'])
    def test_zero_target_active_games_are_retained(self):
        stats,_=fixture();stats=stats.iloc[:1].copy()
        snaps=pd.DataFrame([dict(pfr_player_id='p1',offense_snaps=20,offense_pct=.3,season=2025,week=1,team='SEA',position='WR',player='Zero Receiver',game_type='REG')])
        players=pd.DataFrame([dict(pfr_id='p1',gsis_id='zero')])
        joined,q=add_snap_zeros(stats,snaps,players)
        zero=joined[joined.player_id=='zero'].iloc[0]
        self.assertEqual(zero.targets,0);self.assertEqual(q['addedZeroTargetGames'],1)
    def test_route_current_total_does_not_match_past_or_other_team(self):
        from types import SimpleNamespace
        p=SimpleNamespace(player_display_name='Test Receiver',team='SEA')
        snap={'WR':{'asOf':'2026-11-01T00:00:00Z','players':[{'profileUrl':'/players/id/test-receiver/','label':'SEA T. Receiver'}]}}
        self.assertIsNotNone(match_snapshot(p,snap,2026,pd.Timestamp('2026-11-02',tz='UTC')))
        self.assertIsNone(match_snapshot(p,snap,2026,pd.Timestamp('2026-10-02',tz='UTC')))
        p.team='SF';self.assertIsNone(match_snapshot(p,snap,2026,pd.Timestamp('2026-11-02',tz='UTC')))
    def test_partial_week_is_not_final_completed_week_holdout(self):
        stats,sched=fixture();frame,features=prepare(stats,sched,now='2027-01-01T00:00:00Z')
        r=walk_forward(frame,features,2026,trees=3,min_train=20,complete_weeks={1,2,3,4,5,6,7})
        self.assertEqual(r['latestWeekHoldout']['week'],7)
        self.assertEqual(r['partialWeeks'],[8])
    def test_upcoming_forecast_features_and_samples_exist(self):
        stats,sched=fixture()
        future=sched[(sched.season==2026)&(sched.week==8)].copy()
        future['week']=10;future['game_id']='2026_10_SEA_SF';future['kickoff']=pd.Timestamp('2026-11-08T20:00:00Z');future['completed']=False
        frame,features=prepare(stats,pd.concat([sched,future]),now='2026-11-06T00:00:00Z')
        f=frame[frame.forecast];history=frame[(~frame.forecast)&(frame.prior_games>=3)]
        self.assertEqual(len(f),8)
        self.assertTrue(f.receiving_yards.isna().all())
        model=DistributionForest(trees=3,min_leaf=5).fit(history[features],history[['receiving_yards','receptions']])
        self.assertEqual(model.sample(f[features],32).shape,(8,32,2))
    def test_bad_odds_fail(self):
        for value in [0,99,float('nan')]:
            with self.assertRaises(ValueError):decimal(value)

if __name__=='__main__':unittest.main()
