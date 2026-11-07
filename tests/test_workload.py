import unittest
from datetime import datetime,timezone
from edge.workload import build_context
from edge.return_reports import collect
class WorkloadTests(unittest.TestCase):
 def fixture(self):
  history=lambda pid,c:[{'gameId':f'2026_0{i}_B_A','season':2026,'team':'A','kickoff':f'2026-10-{i:02d}T18:00:00Z','carries':v,'rushing_yards':v*4,'rushing_tds':0} for i,v in c]
  players=[{'playerId':'s','name':'Starter','team':'A','position':'RB','history':history('s',[(1,18),(2,18)])},{'playerId':'b','name':'Backup','team':'A','position':'RB','history':history('b',[(1,2),(2,2),(3,20),(4,20),(5,20)])}]
  f={'playerId':'b','name':'Backup','team':'A','position':'RB','opponent':'B','homeTeam':'A','awayTeam':'B','gameId':'2026_09_B_A','kickoff':'2026-11-08T18:00:00Z','features':{'carries_last3':20},'marketSamples':{'player_rush_attempts':{'values':[20]*32,'mean':20}}}
  b={'season':2026,'generatedAt':'m','players':players,'forecasts':[f]};h={'season':2026,'week':9,'injuries':{},'roster':[{'playerId':'s','name':'Starter','team':'A','position':'RB','fresh':True,'listedStarter':True,'expectedStarter':True},{'playerId':'b','name':'Backup','team':'A','position':'RB','fresh':True,'listedStarter':False,'expectedStarter':False}]}
  return b,h
 def test_returner_recovered_and_backup_reduced_with_conserved_volume(self):
  b,h=self.fixture();c=build_context(b,h,datetime(2026,11,7,tzinfo=timezone.utc),32);self.assertEqual(c['newForecasts'][0]['playerId'],'s');self.assertLess(c['players']['b']['channels']['carries']['expected'],20)
  for g in c['groups']:self.assertEqual(g['budgetMean'],g['allocatedMean'])
 def test_official_out_without_report_is_not_activated(self):
  b,h=self.fixture();h['injuries']['s']={'status':'OUT','ruledOut':True};self.assertFalse(build_context(b,h,datetime(2026,11,7,tzinfo=timezone.utc))['players'])
 def test_potential_return_does_not_override_official_out(self):
  b,h=self.fixture();h['injuries']['s']={'status':'OUT','ruledOut':True};h['returnReports']={'reports':[{'playerId':'s','source':'https://example.org'}]};c=build_context(b,h,datetime(2026,11,7,tzinfo=timezone.utc));self.assertFalse(c['newForecasts']);self.assertTrue(c['players']['b']['channels']['carries']['scenarioOnly']);self.assertLess(c['players']['b']['channels']['carries']['expected'],20)
 def test_insufficient_shared_history_is_not_filled_with_zero(self):
  b,h=self.fixture();b['players'][1]['history']=b['players'][1]['history'][2:];c=build_context(b,h,datetime(2026,11,7,tzinfo=timezone.utc));self.assertNotIn('b',c['players'])
 def test_future_rows_excluded(self):
  b,h=self.fixture();b['players'][0]['history'].append({'gameId':'future','season':2026,'team':'A','kickoff':'2027-01-01T18:00:00Z','carries':1000});a=build_context(b,h,datetime(2026,11,7,tzinfo=timezone.utc),32);self.assertLess(a['players']['s']['channels']['carries']['expected'],100)
 def test_source_failure_disclosed(self):
  b,h=self.fixture();r=collect(b,h,datetime(2026,11,7,tzinfo=timezone.utc),fetch=lambda url:(_ for _ in ()).throw(ValueError()));self.assertTrue(r['coverage']);self.assertTrue(all(s['status']=='unavailable' for s in r['coverage']));self.assertFalse(r['reports'])
if __name__=='__main__':unittest.main()
