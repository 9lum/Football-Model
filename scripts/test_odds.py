import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.refresh_odds import collect, request_plan, ProviderError
class OddsTests(unittest.TestCase):
    def test_quota_budget(self):
        budget,markets,regions,cost=request_plan(500)
        self.assertLessEqual(cost,budget);self.assertEqual(len(markets),3)
        self.assertLessEqual(request_plan(1)[0],1)
        self.assertEqual(request_plan(10000,'44')[3],22)
    def test_safe_failure_retains_original_timestamps(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);old={'id':'a','commence_time':'2026-11-08T18:00:00Z','collectedAt':'2026-11-05T00:00:00Z','bookmakers':[]}
            (p/'odds.json').write_text(json.dumps({'data':[old]}))
            with patch('scripts.refresh_odds.fetch',side_effect=ProviderError(401)):
                r=collect(p,'secret',dt.datetime(2026,11,6,tzinfo=dt.timezone.utc))
            self.assertEqual(r['data'][0]['collectedAt'],old['collectedAt']);self.assertNotIn('secret',(p/'odds.json').read_text());self.assertEqual(r['errors'][0]['code'],401)
    def test_response_is_published_and_archived(self):
        event={'id':'a','home_team':'Seattle Seahawks','away_team':'Arizona Cardinals','commence_time':'2026-11-08T18:00:00Z'}
        odds={**event,'bookmakers':[{'title':'Test Book','markets':[{'key':'player_pass_yds','last_update':'2026-11-06T00:00:00Z','outcomes':[{'price':-110}]}]}]}
        with tempfile.TemporaryDirectory() as d,patch('scripts.refresh_odds.fetch',side_effect=[([event],{'remaining':'500'}),(odds,{'last':'3','remaining':'497'})]):
            r=collect(Path(d),'secret',dt.datetime(2026,11,6,tzinfo=dt.timezone.utc));self.assertEqual(r['status'],'ok');self.assertEqual(r['quoteCount'],1);self.assertEqual(len(json.loads((Path(d)/'odds-history.json').read_text())['snapshots']),1)
