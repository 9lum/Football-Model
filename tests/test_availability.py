import importlib.util
import unittest
import pandas as pd
from edge.availability import game_status,latest_depth,match_and_resolve,roster_roles,qb_replacement_parameters
from edge.context import summarize_defense,attach_defense,current_team_map

class AvailabilityTests(unittest.TestCase):
    def test_designations_and_official_out_have_distinct_semantics(self):
        self.assertEqual(game_status('Questionable'),'QUESTIONABLE');self.assertEqual(game_status('Doubtful'),'DOUBTFUL');self.assertEqual(game_status('Did not participate'),'UNSPECIFIED')
        now=pd.Timestamp('2026-11-06',tz='UTC');profile=[{'playerId':'p','name':'Test QB','team':'SEA'}]
        records=[dict(name='Test QB',team='SEA',gameStatus='OUT',practice='DNP',injury='Thumb',authority='official',scopeVerified=True,season=2026,week=9,observedAt=now.isoformat(),source='https://www.nfl.com/injuries/')]
        resolved,_=match_and_resolve(records,[],profile,2026,9,now)
        self.assertTrue(resolved['p']['ruledOut'])
        records[0]['gameStatus']='UNSPECIFIED';resolved,_=match_and_resolve(records,[],profile,2026,9,now);self.assertFalse(resolved['p']['ruledOut'])
    def test_secondary_report_is_not_official_confirmation(self):
        now=pd.Timestamp('2026-11-06',tz='UTC');r=dict(name='Test QB',team='SEA',gameStatus='OUT',practice=None,authority='secondary',scopeVerified=False,season=2026,week=9,observedAt=now.isoformat(),source='https://espn.com')
        resolved,_=match_and_resolve([r],[],[dict(playerId='p',name='Test QB',team='SEA')],2026,9,now)
        self.assertFalse(resolved['p']['ruledOut']);self.assertTrue(resolved['p']['reviewRequired'])
    def test_depth_snapshot_and_replacement_order(self):
        d=pd.DataFrame([dict(dt='2026-11-05T10:00:00Z',team='SEA',player_name='Starter',gsis_id='s',pos_abb='QB',pos_slot=0,pos_rank=1),dict(dt='2026-11-05T10:00:00Z',team='SEA',player_name='Backup',gsis_id='b',pos_abb='QB',pos_slot=0,pos_rank=2)])
        roles=roster_roles(latest_depth(d,pd.Timestamp('2026-11-06',tz='UTC')),{'s':{'ruledOut':True}})
        self.assertTrue(next(r for r in roles if r['playerId']=='b')['expectedStarter']);self.assertFalse(next(r for r in roles if r['playerId']=='s')['expectedStarter'])
    def test_pick_assets_are_not_misread_as_player_trades(self):
        people=pd.DataFrame([dict(pfr_id='P1',gsis_id='p')]);depth=[dict(playerId='p',team='SEA',fresh=True,asOf='2026-11-05T00:00:00Z')]
        trades=pd.DataFrame([dict(pfr_id='P1',trade_date='2026-10-01',gave='SEA',received='BUF',pick_season=2027)])
        mapping,notes=current_team_map(depth,trades,people,pd.Timestamp('2026-11-06',tz='UTC'));self.assertEqual(mapping['p'],'SEA');self.assertEqual(notes,{})
    @unittest.skipUnless(importlib.util.find_spec('bs4'),'BeautifulSoup is installed by the hosted workflow')
    def test_public_official_table_scope(self):
        from edge.availability import parse_official
        html='<h1>2026 NFL Injury Report</h1><h2>WEEK 9</h2><h3>Seahawks</h3><table><thead><tr><th>Player</th><th>Position</th><th>Injuries</th><th>Practice Status</th><th>Game Status</th></tr></thead><tbody><tr><td>Test QB</td><td>QB</td><td>Thumb</td><td>DNP</td><td>Doubtful</td></tr></tbody></table>'
        rows=parse_official(html,'https://nfl.com/injuries',2026,9,'2026-11-06T00:00:00Z',True);self.assertEqual(rows[0]['gameStatus'],'DOUBTFUL')
        with self.assertRaises(ValueError):parse_official(html,'https://nfl.com/injuries',2026,10,'2026-11-06T00:00:00Z',True)

class DefensiveTests(unittest.TestCase):
    def test_contact_rate_is_not_falsely_called_pressure(self):
        d=pd.DataFrame([dict(game_id='2025_01_BUF_SEA',play_id=i,season=2025,week=1,season_type='REG',defteam='SEA',qb_dropback=1,rush_attempt=0,qb_kneel=0,epa=.2,sack=i==0,qb_hit=i<2,yards_gained=10,complete_pass=1,receiver_player_id='p') for i in range(4)])
        games,receiver=summarize_defense(d);self.assertEqual(games.iloc[0].qb_contact_rate,.5);self.assertTrue(pd.isna(games.iloc[0].pressure_rate));self.assertEqual(games.iloc[0].man_count,0)
    def test_roster_override_only_affects_upcoming_team(self):
        from test_engine import fixture
        from edge.features import prepare
        stats,sched=fixture();future=sched[(sched.season==2026)&(sched.week==8)].copy();future['week']=10;future['game_id']='2026_10_SEA_SF';future['kickoff']=pd.Timestamp('2026-11-08',tz='UTC');future['completed']=False
        frame,_=prepare(stats,pd.concat([sched,future]),now='2026-11-06T00:00:00Z',current_teams={'SEA0':'SF'})
        self.assertEqual(frame[(frame.player_id=='SEA0')&frame.forecast].team.iloc[0],'SF');self.assertTrue(frame[(frame.player_id=='SEA0')&~frame.forecast].team.eq('SEA').all())
if __name__=='__main__':unittest.main()

class ContextTimingTests(unittest.TestCase):
    def test_current_coverage_snapshot_never_backfills_historical_tests(self):
        from test_engine import fixture
        from edge.features import prepare
        stats,schedules=fixture();frame,features=prepare(stats,schedules,now='2027-01-01T00:00:00Z')
        rows=[]
        for r in schedules.itertuples():
            row={'game_id':r.game_id,'season':r.season,'week':r.week,'team':r.team,'man_count':5,'zone_count':15,'dropbacks':20}
            for key in ['pass_epa_allowed','rush_epa_allowed','pass_success_allowed','rush_success_allowed','sack_rate','qb_contact_rate','explosive_pass_rate','explosive_rush_rate','pressure_rate','five_plus_rusher_rate']:row[key]=r.week/100
            rows.append(row)
        defense=pd.DataFrame(rows)
        a,added=attach_defense(frame,features,defense,pd.DataFrame(),schedules,{'SEA':{'man':.99,'zone':.01,'asOf':'2026-10-01T00:00:00Z'}})
        self.assertTrue(a.loc[a.season.eq(2026),'matchup_man_rate'].eq(.25).all())
        poisoned=defense.copy();poisoned.loc[(poisoned.season==2026)&(poisoned.week>=5),'pass_epa_allowed']=999
        b,_=attach_defense(frame,features,poisoned,pd.DataFrame(),schedules)
        mask=a.season.eq(2026)&a.week.eq(5)
        self.assertEqual(a.loc[mask,'matchup_pass_epa_allowed'].tolist(),b.loc[mask,'matchup_pass_epa_allowed'].tolist())
