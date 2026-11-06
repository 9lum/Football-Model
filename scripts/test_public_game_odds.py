import datetime as dt
import unittest
from scripts.refresh_public_game_odds import parse
class PublicOddsTests(unittest.TestCase):
 def test_prices_are_explicit_and_observation_is_not_provider_time(self):
  payload={'events':[{'id':'one','date':'2026-11-08T18:00Z','status':{'type':{'completed':False}},'competitions':[{'competitors':[{'homeAway':'home','team':{'displayName':'Home'}},{'homeAway':'away','team':{'displayName':'Away'}}],'odds':[{'provider':{'id':100,'name':'DraftKings'},'moneyline':{'home':{'close':{'odds':'-150'}}},'pointSpread':{'home':{'close':{'line':'-3','odds':'-110'}}},'total':{'over':{'close':{'line':'o44.5','odds':'-105'}}}}]}]}]}
  rows=parse(payload,'2026-11-06T00:00:00Z',dt.datetime(2026,11,6,tzinfo=dt.timezone.utc));b=rows[0]['bookmakers'][0];self.assertIsNone(b['last_update']);self.assertEqual(b['markets'][2]['outcomes'][0]['point'],44.5);self.assertEqual(b['markets'][0]['outcomes'][0]['price'],-150);self.assertEqual(len(b['markets'][0]['outcomes']),1)
