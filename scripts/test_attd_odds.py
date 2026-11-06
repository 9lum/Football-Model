import datetime as dt,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.refresh_attd_odds import collect,MARKETS
from scripts.refresh_odds import ProviderError
class ATTDContracts(unittest.TestCase):
 def test_documented_first_td_market_is_requested_and_global_validation_errors_stop(self):
  self.assertEqual(MARKETS,['player_anytime_td','player_1st_td','player_last_td']);events=[{'id':str(i),'commence_time':'2026-11-08T18:00:00Z'} for i in range(3)]
  with tempfile.TemporaryDirectory() as directory,patch('scripts.refresh_attd_odds.fetch',side_effect=[(events,{'remaining':'500'}),ProviderError(422)]) as fetch:
   collect(Path(directory),'secret',dt.datetime(2026,11,6,tzinfo=dt.timezone.utc));self.assertEqual(fetch.call_count,2);self.assertEqual(fetch.call_args.kwargs['markets'],'player_anytime_td,player_1st_td,player_last_td')
