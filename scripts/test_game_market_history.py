import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from scripts.game_market_history import append_history

def event(price=-110,point=44.5,source=None,updated='2026-11-07T10:00:00Z'):
 b={'key':'dk','title':'DraftKings','markets':[{'key':'totals','last_update':updated,'outcomes':[{'name':'Over','price':price,'point':point}]}]}
 if source:b['source']=source;b['last_update']=None;b['markets'][0]['last_update']=None
 return {'id':'one','home_team':'Home','away_team':'Away','commence_time':'2026-11-08T18:00:00Z','bookmakers':[b]}
class HistoryTests(unittest.TestCase):
 def test_first_price_unchanged_and_price_only_or_point_changes(self):
  with tempfile.TemporaryDirectory() as tmp:
   append_history(tmp,[event()],'2026-11-07T10:01:00Z');append_history(tmp,[event()],'2026-11-07T10:02:00Z');append_history(tmp,[event(-105)],'2026-11-07T10:03:00Z');h=append_history(tmp,[event(-105,45)],'2026-11-07T10:04:00Z');self.assertEqual(len(h['observations']),3);self.assertEqual(h['observations'][0]['observedAt'],'2026-11-07T10:01:00Z');self.assertEqual(h['observations'][2]['point'],45)
 def test_provider_isolation_and_no_fabricated_public_provider_timestamp(self):
  with tempfile.TemporaryDirectory() as tmp:
   append_history(tmp,[event()],'2026-11-07T10:01:00Z');h=append_history(tmp,[event(-105,source='ESPN public scoreboard')],'2026-11-07T10:02:00Z');self.assertEqual(len(h['observations']),2);self.assertIsNone(h['observations'][-1]['providerUpdatedAt'])
 def test_rejects_out_of_order_and_ambiguous_outcomes(self):
  with tempfile.TemporaryDirectory() as tmp:
   append_history(tmp,[event()],'2026-11-07T10:01:00Z');append_history(tmp,[event(-105,updated='2026-11-06T10:00:00Z')],'2026-11-07T10:02:00Z');bad=event();bad['bookmakers'][0]['markets'][0]['outcomes']*=2;h=append_history(tmp,[bad],'2026-11-07T10:03:00Z');self.assertEqual(len(h['observations']),1)
 def test_distinct_kickoff_is_not_the_same_game(self):
  with tempfile.TemporaryDirectory() as tmp:
   append_history(tmp,[event()],'2026-11-07T10:01:00Z');other=event(-105);other['commence_time']='2026-11-15T18:00:00Z';h=append_history(tmp,[other],'2026-11-07T10:02:00Z');self.assertEqual(len(h['observations']),2);self.assertNotEqual(h['observations'][0]['gameKey'],h['observations'][1]['gameKey'])
if __name__=='__main__':unittest.main()
