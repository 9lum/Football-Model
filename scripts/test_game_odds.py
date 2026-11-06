import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.refresh_game_odds import collect,refresh_minutes
from scripts.refresh_odds import ProviderError
NOW=dt.datetime(2026,11,6,tzinfo=dt.timezone.utc)
class GameOddsTests(unittest.TestCase):
 def test_quota_aware_interval_and_override(self):
  self.assertGreater(refresh_minutes(500,3),15);self.assertEqual(refresh_minutes(500,3,'15'),15);self.assertEqual(refresh_minutes(500,3,'1'),15)
 def test_collects_all_games_with_three_standard_markets(self):
  events=[{'id':'a','home_team':'Seattle Seahawks','away_team':'Arizona Cardinals','commence_time':'2026-11-08T18:00:00Z','bookmakers':[{'title':'Book','markets':[{'key':key,'last_update':'2026-11-05T23:59:00Z','outcomes':[{'name':'Over','point':44.5,'price':-110}]} for key in ['h2h','spreads','totals']]}]}]
  with tempfile.TemporaryDirectory() as d,patch('scripts.refresh_game_odds.fetch',side_effect=[([] ,{'remaining':'490'}),(events,{'last':'3','remaining':'487'})]) as fetch:
   r=collect(Path(d),'private-test-key',NOW);self.assertEqual(r['quoteCount'],3);self.assertEqual(fetch.call_args.kwargs['markets'],'h2h,spreads,totals');self.assertNotIn('private-test-key',(Path(d)/'game-odds.json').read_text());self.assertEqual(r['data'][0]['bookmakers'][0]['markets'][0]['last_update'],'2026-11-05T23:59:00Z')
 def test_skip_before_due_and_preserve_quotes_on_failure(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);old={'generatedAt':'2026-11-05T00:00:00Z','nextRefreshAt':'2026-11-07T00:00:00Z','data':[{'commence_time':'2026-11-08T18:00:00Z','collectedAt':'2026-11-05T00:00:00Z','bookmakers':[]}]};(p/'game-odds.json').write_text(json.dumps(old))
   with patch('scripts.refresh_game_odds.fetch') as fetch:self.assertEqual(collect(p,'key',NOW),old);fetch.assert_not_called()
   with patch('scripts.refresh_game_odds.fetch',side_effect=ProviderError(401)):
    r=collect(p,'key',NOW,force=True);self.assertEqual(r['data'][0]['collectedAt'],old['data'][0]['collectedAt']);self.assertEqual(r['errors'][0]['code'],401)
