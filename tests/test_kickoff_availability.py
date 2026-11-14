import datetime as dt,unittest
from unittest.mock import patch
UTC=dt.timezone.utc
class FinalAvailabilityTests(unittest.TestCase):
 def test_final_refresh_rejects_mislabeled_player_identity(self):
  import pandas as pd,gzip
  from scripts.kickoff_refresh import refresh_availability
  depth=pd.DataFrame([{'dt':'2026-11-14T21:00Z','team':'DET','player_name':'Tyler Conklin','gsis_id':'a','pos_abb':'TE','pos_slot':1,'pos_rank':1},{'dt':'2026-11-14T21:00Z','team':'DET','player_name':'Tyler Conklin','gsis_id':'b','pos_abb':'TE','pos_slot':1,'pos_rank':2}])
  people=pd.DataFrame([{'gsis_id':'a','display_name':'Tyler Conklin'},{'gsis_id':'b','display_name':'Ryan Izzo'}]);now=dt.datetime(2026,11,14,22,tzinfo=UTC)
  previous={'roster':[{'playerId':'safe','team':'DET','position':'TE','slot':1,'rank':1,'fresh':True}],'injuries':{}}
  class Response:
   def __init__(self,raw):self.raw=raw
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):return self.raw
  def response(request,**kwargs):
   if 'depth_charts' in request.full_url:return Response(gzip.compress(depth.to_csv(index=False).encode()))
   if '/players/' in request.full_url:return Response(gzip.compress(people.to_csv(index=False).encode()))
   return Response(b'{}')
  batch=[{'gameId':'2026_10_NE_DET','homeTeam':'DET','awayTeam':'NE'}]
  with patch('scripts.kickoff_refresh.read',side_effect=lambda path,default:{'season':2026,'players':[]} if path.name=='latest.json' else previous),patch('scripts.kickoff_refresh.urlopen',side_effect=response),patch('scripts.kickoff_refresh.stamp',return_value=now),patch('pandas.Timestamp.now',return_value=pd.Timestamp(now)),patch('edge.availability.parse_espn',return_value=[]),patch('edge.availability.parse_official',return_value=[]),patch('scripts.kickoff_refresh.save') as save:
   refresh_availability(batch);written=save.call_args.args[1];self.assertEqual([r['playerId'] for r in written['roster']],['a'])

  previous['roster']=[{'playerId':'safe','name':'Safe Player','team':'DET','position':'TE','slot':1,'rank':1,'fresh':True}]
  def failed_registry(request,**kwargs):
   if '/players/' in request.full_url:raise OSError('Registry unavailable')
   return response(request,**kwargs)
  with patch('scripts.kickoff_refresh.read',side_effect=lambda path,default:{'season':2026,'players':[]} if path.name=='latest.json' else previous),patch('scripts.kickoff_refresh.urlopen',side_effect=failed_registry),patch('scripts.kickoff_refresh.stamp',return_value=now),patch('pandas.Timestamp.now',return_value=pd.Timestamp(now)),patch('edge.availability.parse_espn',return_value=[]),patch('edge.availability.parse_official',return_value=[]),patch('scripts.kickoff_refresh.save') as save:
   refresh_availability(batch);self.assertEqual([r['playerId'] for r in save.call_args.args[1]['roster']],['safe'])
