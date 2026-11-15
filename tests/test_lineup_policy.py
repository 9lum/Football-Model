import unittest,datetime as dt
from edge.lineup_policy import build_lineup_policy,apply_touchdown_lineup
UTC=dt.timezone.utc
class LineupTests(unittest.TestCase):
 def fixture(self):
  now=dt.datetime(2026,11,15,20,tzinfo=UTC);kickoff='2026-11-15T21:05:00Z';gid='2026_10_SEA_LV'
  hist=lambda weeks:[{'gameId':f'2026_0{w}_SEA_A','season':2026,'team':'SEA','kickoff':f'2026-11-0{w-2}T18:00:00Z','carries':n,'targets':0} for w,n in weeks]
  bundle={'season':2026,'generatedAt':'m','players':[{'playerId':'starter','history':hist([(8,6),(9,16)])},{'playerId':'backup','history':hist([(6,20),(7,24)])}], 'forecasts':[{'playerId':p,'team':'SEA','gameId':gid,'kickoff':kickoff} for p in ['starter','backup']]}
  health={'season':2026,'week':10,'generatedAt':now.isoformat(),'injuries':{},'roster':[{'playerId':'starter','position':'RB','team':'SEA','fresh':True,'rank':1,'expectedStarter':True},{'playerId':'backup','position':'RB','team':'SEA','fresh':True,'rank':4,'expectedStarter':False}]}
  return now,bundle,health
 def test_old_starter_volume_does_not_support_a_current_deep_backup_offer(self):
  now,b,h=self.fixture();p=build_lineup_policy(b,h,now);self.assertIn('backup',p['players']);self.assertNotIn('starter',p['players']);self.assertEqual(p['players']['backup']['evidence']['recordedOpportunities'],[None,None])
 def test_recent_offensive_role_and_promotions_remain_eligible(self):
  now,b,h=self.fixture();h['roster'][1]['expectedStarter']=True;self.assertNotIn('backup',build_lineup_policy(b,h,now)['players']);h['roster'][1]['expectedStarter']=False;b['players'][1]['history']=b['players'][0]['history'];self.assertNotIn('backup',build_lineup_policy(b,h,now)['players'])
 def test_out_is_unavailable_not_a_zero_probability_and_old_games_are_preserved(self):
  now,b,h=self.fixture();h['injuries']['backup']={'status':'OUT','ruledOut':True};policy=build_lineup_policy(b,h,now);f=b['forecasts'][1];g={'gameId':f['gameId'],'kickoff':f['kickoff'],'players':[{'playerId':'backup','probability':.503}],'candidates':[]};report={'games':[g], 'allPlayerOdds':{'backup':{**f,'status':'model estimate','markets':{'player_anytime_td':{'probability':.503}}}}};r=apply_touchdown_lineup(report,policy,now);self.assertEqual(r['allPlayerOdds']['backup']['markets'],{});self.assertEqual(r['allPlayerOdds']['backup']['status'],'unavailable');self.assertEqual(r['games'][0]['players'],[]);self.assertEqual(report['games'][0]['players'][0]['probability'],.503);later=now+dt.timedelta(days=1);self.assertEqual(apply_touchdown_lineup(report,policy,later)['games'],report['games'])
 def test_stale_health_cannot_change_an_upcoming_projection(self):
  now,b,h=self.fixture();h['generatedAt']=(now-dt.timedelta(days=1)).isoformat();self.assertEqual(build_lineup_policy(b,h,now)['players'],{})

 def test_untrusted_old_out_text_does_not_override_a_current_starting_role(self):
  now,b,h=self.fixture();h['injuries']['starter']={'status':'OUT','ruledOut':False,'confirmed':False,'selectionTrusted':False};self.assertNotIn('starter',build_lineup_policy(b,h,now)['players'])
