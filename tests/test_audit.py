import unittest
from types import SimpleNamespace
import pandas as pd
from edge.audit import update_ledger

class AuditTests(unittest.TestCase):
    def fixture(self):
        f={'playerId':'qb','name':'Test QB','position':'QB','team':'BUF','opponent':'SEA','gameId':'2026_09_SEA_BUF','kickoff':'2026-11-08T20:00:00Z','marketSamples':{'player_pass_yds':{'mean':240.,'p10':150,'p90':320,'validationPassed':True}}}
        return {'schemaVersion':3,'forecasts':[f]}
    def test_pre_kickoff_projection_is_frozen_and_scored_against_later_actuals(self):
        snapshot=self.fixture();pub={'issuedAt':'2026-11-06T00:00:00Z','commit':'a'*40}
        actual=pd.DataFrame([{'game_id':'2026_09_SEA_BUF','player_id':'qb','passing_yards':260}])
        ledger,report=update_ledger([],snapshot,pub,actual,2026,pd.Timestamp('2026-11-09',tz='UTC'))
        self.assertEqual(report['rows'][0]['actual'],260);self.assertEqual(report['rows'][0]['error'],20)
        snapshot['forecasts'][0]['marketSamples']['player_pass_yds']['mean']=280
        ledger,report=update_ledger(ledger,snapshot,pub,actual,2026,pd.Timestamp('2026-11-10',tz='UTC'))
        self.assertEqual(len(ledger),1);self.assertEqual(report['rows'][0]['projected'],240)
    def test_post_kickoff_publication_is_not_backfilled(self):
        ledger,report=update_ledger([],self.fixture(),{'issuedAt':'2026-11-09T00:00:00Z','commit':'b'*40},pd.DataFrame(columns=['game_id','player_id']),2026,pd.Timestamp('2026-11-10',tz='UTC'))
        self.assertEqual(ledger,[])
    def test_missing_outcome_is_not_assumed_zero_or_scored(self):
        ledger,report=update_ledger([],self.fixture(),{'issuedAt':'2026-11-06T00:00:00Z','commit':'a'*40},pd.DataFrame(columns=['game_id','player_id']),2026,pd.Timestamp('2026-11-09',tz='UTC'))
        self.assertIsNone(report['rows'][0]['actual']);self.assertEqual(report['rows'][0]['status'],'awaiting_stats_or_participation')
    def test_unverifiable_publication_is_not_claimed_as_issued(self):
        ledger,_=update_ledger([],self.fixture(),None,pd.DataFrame(columns=['game_id','player_id']),2026,pd.Timestamp('2026-11-09',tz='UTC'))
        self.assertEqual(ledger,[])
if __name__=='__main__':unittest.main()
