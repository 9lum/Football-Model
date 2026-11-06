import datetime as dt,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.kickoff_refresh import plan,due_games,collect_final,merge_event,sources_unchanged,MARKETS
from scripts.odds_quota import routine_budget,kickoff_reserve
UTC=dt.timezone.utc
class PregameTests(unittest.TestCase):
 def test_deadline_and_target_are_utc_and_each_game_is_scheduled(self):
  now=dt.datetime(2026,11,8,17,20,tzinfo=UTC);game={'gameId':'2026_09_SEA_SF','kickoff':'2026-11-08T18:00:00+00:00'}
  with patch('scripts.kickoff_refresh.games',return_value=[game]),patch('scripts.kickoff_refresh.read',return_value={}):p=plan(now)
  self.assertEqual(p['games'][0]['targetAt'],'2026-11-08T17:53:30+00:00');self.assertEqual(p['games'][0]['deadlineAt'],'2026-11-08T17:55:00+00:00');self.assertEqual(len(due_games(p,now)),1);p['games'][0]['publishedAt']=now.isoformat();self.assertEqual(due_games(p,now),[])
 def test_routine_collections_cannot_spend_reserved_kickoff_credits(self):
  now=dt.datetime(2026,11,6,tzinfo=UTC);reserve=kickoff_reserve(now);self.assertEqual(routine_budget(reserve,50,now),0);self.assertEqual(routine_budget(reserve+8,50,now),8)
 def test_old_book_timestamps_remain_old_when_another_book_is_refreshed(self):
  prior={'bookmakers':[{'key':'old','title':'Old','markets':[{'key':'player_anytime_td','last_update':'old','outcomes':[]}]}]};fresh={'bookmakers':[{'key':'new','title':'New','markets':[{'key':'player_1st_td','last_update':'new','outcomes':[]}]}]};merged=merge_event(prior,fresh,MARKETS[:3]);self.assertEqual(merged['bookmakers'][0]['markets'][0]['last_update'],'old');self.assertEqual(len(merged['bookmakers']),2)
 def test_source_changes_or_missing_sources_invalidate_current_stats_claim(self):
  self.assertTrue(sources_unchanged({'p':{'sha256':'x'}},{'p':{'status':'ok','sha256':'x'}}));self.assertFalse(sources_unchanged({'p':{'sha256':'x'}},{'p':{'status':'ok','sha256':'y'}}));self.assertFalse(sources_unchanged({'p':{'sha256':'x'}},{'p':{'status':'unavailable'}}))
 def test_final_collector_fails_closed_when_quota_cannot_fund_all_markets(self):
  now=dt.datetime(2026,11,8,17,53,tzinfo=UTC);g={'gameId':'g','homeTeam':'SEA','awayTeam':'SF','kickoff':'2026-11-08T18:00:00+00:00'};event={'id':'e','home_team':'Seattle Seahawks','away_team':'San Francisco 49ers','commence_time':g['kickoff']}
  with tempfile.TemporaryDirectory() as directory,patch('scripts.kickoff_refresh.DATA',Path(directory)),patch('scripts.kickoff_refresh.stamp',return_value=now),patch('scripts.kickoff_refresh.fetch',return_value=([event],{'remaining':'5'})) as fetch:
   result=collect_final([g],key='not-printed',now=now);self.assertEqual(result['g']['error'],'insufficient_quota');self.assertEqual(fetch.call_count,1)
 def test_final_collection_includes_all_three_td_markets_and_retains_provider_time(self):
  now=dt.datetime(2026,11,8,17,53,30,tzinfo=UTC);g={'gameId':'g','homeTeam':'SEA','awayTeam':'SF','kickoff':'2026-11-08T18:00:00+00:00'};event={'id':'e','home_team':'Seattle Seahawks','away_team':'San Francisco 49ers','commence_time':g['kickoff']};payload={**event,'bookmakers':[{'key':'test','title':'Test','markets':[{'key':k,'last_update':'2026-11-08T17:53:00+00:00','outcomes':[{'name':'Yes','description':'Player','price':150}]} for k in MARKETS]}]}
  with tempfile.TemporaryDirectory() as directory,patch('scripts.kickoff_refresh.DATA',Path(directory)),patch('scripts.kickoff_refresh.stamp',return_value=now),patch('scripts.kickoff_refresh.fetch',side_effect=[([event],{'remaining':'100'}),(payload,{'remaining':'94'})]) as fetch:
   result=collect_final([g],key='not-printed',now=now);self.assertEqual(result['g']['status'],'collected');self.assertTrue(result['g']['sourceQuotesCurrent']);self.assertIn('player_1st_td',result['g']['markets']);saved=json.loads((Path(directory)/'attd-odds.json').read_text());self.assertEqual(saved['data'][0]['bookmakers'][0]['markets'][0]['last_update'],'2026-11-08T17:53:00+00:00');self.assertEqual(fetch.call_args.kwargs['timeout'],8)
 def test_refreshing_another_market_does_not_redate_an_old_market_via_book_timestamp(self):
  old={'bookmakers':[{'key':'same','last_update':'old','markets':[{'key':'player_anytime_td','outcomes':[]}]}]};new={'bookmakers':[{'key':'same','last_update':'new','markets':[{'key':'player_last_td','last_update':'new','outcomes':[]}]}]};merged=merge_event(old,new,MARKETS[:3]);markets={m['key']:m for m in merged['bookmakers'][0]['markets']};self.assertEqual(markets['player_anytime_td']['last_update'],'old')
