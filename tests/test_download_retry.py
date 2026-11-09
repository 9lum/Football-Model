import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from edge.data import get,BASE
class Response:
 headers={}
 def read(self):return b'fresh'
 def __enter__(self):return self
 def __exit__(self,*args):return False
class DownloadRetryTests(unittest.TestCase):
 def test_release_timeout_retries_a_fresh_asset_request(self):
  url=BASE+'schedules/games.csv'
  with patch('edge.data.urlopen',side_effect=[HTTPError(url,504,'timeout',{},None),Response()]) as request,patch('edge.data.time.sleep'):
   raw,meta=get(url)
  self.assertEqual(raw,b'fresh');self.assertEqual(meta['url'],url);self.assertEqual(request.call_args_list[0].args[0].full_url,url);self.assertIn('?refresh=',request.call_args_list[1].args[0].full_url)
 def test_non_release_sources_do_not_get_unexpected_query_parameters(self):
  url='https://example.com/source'
  with patch('edge.data.urlopen',side_effect=[HTTPError(url,504,'timeout',{},None),Response()]) as request,patch('edge.data.time.sleep'):get(url)
  self.assertEqual(request.call_args_list[1].args[0].full_url,url)

class PlayByPlayRefreshTests(unittest.TestCase):
 def test_current_pbp_uses_same_hourly_asset_path_as_profile_feed(self):
  import io,tempfile
  from pathlib import Path
  import pandas as pd
  from edge.context import parquet_asset
  buffer=io.BytesIO();pd.DataFrame({'game_id':['2026_01_A_B']}).to_parquet(buffer,index=False)
  with tempfile.TemporaryDirectory() as directory,patch('edge.context.get',return_value=(buffer.getvalue(),{})) as download:
   result=parquet_asset('pbp','play_by_play_2026.parquet',['game_id'],Path(directory))
  self.assertIn('?asof=',download.call_args.args[0]);self.assertEqual(len(result),1)
