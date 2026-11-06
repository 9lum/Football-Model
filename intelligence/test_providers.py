import datetime as dt
import os
import unittest
from unittest.mock import patch
from intelligence.providers import venue,xweather_credentials,bdl_pages,ProviderError
class ProviderTests(unittest.TestCase):
    def test_neutral_venues_never_use_home_stadium(self):
        self.assertIsNone(venue({'home_team':'ATL','location':'Neutral','stadium':'Unknown'}))
        self.assertAlmostEqual(venue({'home_team':'ATL','location':'Neutral','stadium':'Wembley Stadium'})[0],51.556)
    def test_weather_requires_both_parts(self):
        with patch.dict(os.environ,{'XWEATHER_API_KEY':'secret','XWEATHER_CLIENT_ID':'id'}):self.assertEqual(xweather_credentials(),('id','secret'))
        with patch.dict(os.environ,{'XWEATHER_API_KEY':'{"client_id":"id","client_secret":"secret"}','XWEATHER_CLIENT_ID':''}):self.assertEqual(xweather_credentials(),('id','secret'))
    def test_pagination_reports_truncation(self):
        with patch('intelligence.providers.request_json',return_value={'data':[{'id':1}],'meta':{'next_cursor':2}}),patch('intelligence.providers.time.sleep'):
            rows,complete=bdl_pages('teams','secret',max_pages=1);self.assertEqual(len(rows),1);self.assertFalse(complete)
