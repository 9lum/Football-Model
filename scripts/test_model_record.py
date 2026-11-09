import unittest
from scripts.model_record import build_record
class RecordTests(unittest.TestCase):
 def setUp(self):
  self.p={'gameId':'2026_09_CIN_ATL','homeTeam':'ATL','awayTeam':'CIN','kickoff':'2026-11-08T18:00Z','projectedAt':'2026-11-08T17:00Z','total':42,'probHomeWin':.3,'probAwayWin':.7}
  self.q={'homeTeam':'Atlanta Falcons','awayTeam':'Cincinnati Bengals','kickoff':self.p['kickoff'],'market':'totals','side':'Over','point':40,'bookKey':'draftkings','book':'DraftKings','observedAt':'2026-11-08T16:00Z'}
  self.s={**self.p,'completed':True,'homeScore':14,'awayScore':24,'scorers':[],'scorersComplete':True}
  self.t={'generatedAt':self.p['projectedAt'],'games':[{**self.p,'players':[{'playerId':'a','name':'Player One','team':'CIN','probability':.5,'health':None}]}]}
 def build(self,prior=None):return build_record(prior or {},{'projections':[self.p]},[self.t],{'results':[self.s]},{'observations':[self.q]},'2026-11-08T22:00Z')
 def test_settlement_and_repeat_refresh_do_not_duplicate_records(self):
  r=self.build();self.assertEqual({x['market']:x['status'] for x in r['rows']},{'moneyline':'win','total':'loss','touchdown':'loss'})
  self.assertEqual(len(self.build(r)['rows']),3)
 def test_late_lines_and_unverified_scoring_never_create_a_grade(self):
  self.q['observedAt']='2026-11-08T17:30Z';self.s['scorersComplete']=False
  statuses={x['market']:x['status'] for x in self.build()['rows']};self.assertEqual(statuses['total'],'ungraded');self.assertEqual(statuses['touchdown'],'ungraded')
 def test_passing_td_does_not_score_and_positive_direct_td_does(self):
  self.s['scorers']=[{'name':'Other Player','team':'CIN','touchdowns':1}]
  self.assertEqual(next(r for r in self.build()['rows'] if r['market']=='touchdown')['status'],'loss')
  self.s['scorers']=[{'name':'Player One','team':'CIN','touchdowns':1}]
  self.assertEqual(next(r for r in self.build()['rows'] if r['market']=='touchdown')['status'],'win')
 def test_push_and_no_retroactive_model_forecasts(self):
  self.s['homeScore']=16
  self.assertEqual(next(r for r in self.build()['rows'] if r['market']=='total')['status'],'push')
  self.p['projectedAt']='2026-11-08T19:00Z';self.t['generatedAt']=self.p['projectedAt'];self.assertEqual(self.build()['rows'],[])
