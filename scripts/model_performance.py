"""All-market proof-of-concept evidence. Published archives and walk-forward tests stay separate."""
import datetime as dt
import json
from pathlib import Path
from scripts.model_record import code,name,same_game,read
from scripts.game_market_history import finite,instant
from edge.config import MARKET_SPECS
DERIVED={'combined_rush_rec_yards':('Rushing + receiving yards','player_rush_yds','player_reception_yds','yards'),'combined_rush_rec_tds':('Rushing + receiving TDs','player_rush_tds','player_reception_tds','count'),'combined_pass_rush_yards':('Passing + rushing yards','player_pass_yds','player_rush_yds','yards')}
GAME_LABELS={'game_home_points':'Home points','game_away_points':'Away points','game_total':'Game total points','game_margin':'Home winning margin','game_moneyline':'Moneyline · home win','player_anytime_td':'Anytime TD','player_1st_td':'First TD','player_last_td':'Last TD'}
def metadata():
 return {**{m:{'label':v[0],'family':'derived','type':'continuous','unit':v[3]} for m,v in DERIVED.items()},**{m:{'label':label,'family':family,'type':'continuous','unit':'yards' if target.endswith('_yards') else 'count'} for m,(label,family,target) in MARKET_SPECS.items()},**{m:{'label':label,'family':'games' if m.startswith('game_') else 'touchdowns','type':'probability' if m=='game_moneyline' or m.startswith('player_') else 'continuous','unit':'probability' if m=='game_moneyline' or m.startswith('player_') else 'points'} for m,label in GAME_LABELS.items()}}
def game_meta(gid):
 parts=gid.split('_');return {'gameId':gid,'season':int(parts[0]),'week':int(parts[1])}
def final_result(p,results):
 matches=[r for r in results if r.get('completed') and same_game(p,r)]
 return matches[0] if len(matches)==1 else None

def build_performance(previous,published,oos,latest,history,td_reports,snapshot,legacy,now):
 rows={r['id']:r for r in previous.get('forecasts',[])};participation={(r.get('gameId'),r.get('playerId')) for r in published.get('rows',[]) if finite(r.get('actual'))};profiles={p['playerId']:p for p in latest.get('players',[])};results=snapshot.get('results',[])
 def put(row):
  old=rows.get(row['id'])
  if old and row['scope']=='published':
   # Preserve forecast, enrich/refresh official outcomes only.
   for key in ['projected','issuedAt','p10','p90','baseline']:row[key]=old.get(key,row.get(key))
   if finite(old.get('actual')) and not finite(row.get('actual')):row.update(actual=old['actual'],actualSource=old.get('actualSource'),status=old.get('status'))
  rows[row['id']]=row
 for r in published.get('rows',[]):
  if r.get('market') not in MARKET_SPECS or instant(r.get('issuedAt')) is None or instant(r.get('kickoff')) is None or instant(r['issuedAt'])>=instant(r['kickoff']):continue
  actual=r.get('actual');actual_source='nflverse published player statistics' if finite(actual) else None
  fixture={'homeTeam':r['gameId'].split('_')[3],'awayTeam':r['gameId'].split('_')[2],'kickoff':r['kickoff']};result=final_result(fixture,results)
  if not result and any(same_game(fixture,s) and not s.get('completed') for s in results):actual=None;actual_source=None
  # Supplement unresolved weekly outcomes with explicitly listed final ESPN box scores.
  if not finite(actual) and result:
   matches=[p for p in result.get('playerStats',[]) if code(p.get('team'))==code(r.get('team')) and name(p.get('name'))==name(r.get('player'))]
   if len(matches)==1:
    actual=matches[0].get('stats',{}).get(r['target']);actual_source='ESPN final box score' if finite(actual) else None
  put({**r,'id':'published:'+r['id'],'scope':'published','entity':r['player'],'type':'continuous','actual':actual if finite(actual) else None,'actualSource':actual_source,'status':'scored' if finite(actual) else r.get('status','pending')})
 for r in oos:
  if not r.get('player_id') or not r.get('game_id'):continue
  profile=profiles.get(r['player_id'],{});historical=next((h for h in profile.get('history',[]) if h.get('gameId')==r['game_id']),{})
  for market,(label,family,target) in MARKET_SPECS.items():
   value=r.get(target)
   if not isinstance(value,dict) or not finite(value.get('actual')) or not finite(value.get('mean')):continue
   put({**game_meta(r['game_id']),'id':'walk_forward:'+r['game_id']+':'+r['player_id']+':'+market,'scope':'walk_forward','market':market,'type':'continuous','entity':profile.get('name',r['player_id']),'playerId':r['player_id'],'position':r.get('position') or profile.get('position'),'team':r.get('team') or historical.get('team'),'projected':value['mean'],'actual':value['actual'],'baseline':value.get('baseline'),'p10':value.get('p10'),'p90':value.get('p90'),'issuedAt':None,'status':'scored','actualSource':'nflverse chronological whole-week test; final-corrected data'})
 groups={}
 for r in list(rows.values()):
  if r.get('playerId') and r.get('market') in MARKET_SPECS:groups.setdefault((r['scope'],r['gameId'],r['playerId'],r.get('issuedAt')), {})[r['market']]=r
 for group in groups.values():
  for market,(label,a,b,unit) in DERIVED.items():
   if a not in group or b not in group:continue
   left,right=group[a],group[b]
   actual=left['actual']+right['actual'] if finite(left.get('actual')) and finite(right.get('actual')) else None
   put({**left,'id':left['scope']+':'+left['gameId']+':'+left['playerId']+':'+market,'market':market,'projected':left['projected']+right['projected'],'actual':actual,'baseline':left['baseline']+right['baseline'] if finite(left.get('baseline')) and finite(right.get('baseline')) else None,'p10':None,'p90':None,'status':'scored' if actual is not None else 'pending','actualSource':'Sum of explicitly observed component stats' if actual is not None else None,'derivedFrom':[a,b],'benchmark':None})
 for p in history.get('projections',[]):
  if instant(p.get('projectedAt')) is None or instant(p.get('kickoff')) is None or instant(p['projectedAt'])>=instant(p['kickoff']):continue
  result=final_result(p,results);base={**game_meta(p['gameId']),'scope':'published','entity':p['awayTeam']+' at '+p['homeTeam'],'kickoff':p['kickoff'],'issuedAt':p['projectedAt'],'position':None,'team':None,'homeTeam':code(p['homeTeam']),'awayTeam':code(p['awayTeam']),'actualSource':'ESPN final score' if result else None}
  specs=[('game_home_points',p.get('homePoints'),result.get('homeScore') if result else None,p.get('homePointsInterval80')),('game_away_points',p.get('awayPoints'),result.get('awayScore') if result else None,p.get('awayPointsInterval80')),('game_total',p.get('total'),result['homeScore']+result['awayScore'] if result else None,p.get('totalInterval80')),('game_margin',-p['homeSpread'] if finite(p.get('homeSpread')) else None,result['homeScore']-result['awayScore'] if result else None,p.get('marginInterval80')),('game_moneyline',p['probHomeWin']/(p['probHomeWin']+p['probAwayWin']) if finite(p.get('probHomeWin')) and finite(p.get('probAwayWin')) and p['probHomeWin']+p['probAwayWin']>0 else p.get('probHomeWin'),int(result['homeScore']>result['awayScore']) if result and result['homeScore']!=result['awayScore'] else None,None)]
  for market,projected,actual,interval in specs:
   if not finite(projected):continue
   put({**base,'id':'published:'+p['gameId']+':'+market,'market':market,'type':'probability' if market=='game_moneyline' else 'continuous','entity':('Home win · '+p['homeTeam']+' vs '+p['awayTeam']) if market=='game_moneyline' else base['entity'],'projected':projected,'actual':actual,'p10':interval[0] if interval else None,'p90':interval[1] if interval else None,'status':'scored' if finite(actual) else 'ungraded_tie' if result else 'pending'})
 for report in td_reports:
  for g in report.get('games',[]):
   issued=g.get('pregameGeneratedAt') or report.get('generatedAt')
   if instant(issued) is None or instant(g.get('kickoff')) is None or instant(issued)>=instant(g['kickoff']):continue
   result=final_result(g,results);entries={}
   for p in g.get('players',[]):entries[p['playerId']]={'name':p['name'],'team':p['team'],'position':p.get('position'),'markets':{'player_anytime_td':{'probability':p['probability']}}}
   for pid,e in g.get('playerTDMarkets',{}).items():
    entry=entries.setdefault(pid,{'name':e.get('name') or profiles.get(pid,{}).get('name',pid),'team':e.get('team'),'markets':{}});entry['markets'].update(e.get('markets',{}))
   for pid,p in entries.items():
    for market,value in p['markets'].items():
     probability=value.get('probability')
     if market not in ['player_anytime_td','player_1st_td','player_last_td'] or not finite(probability) or not 0<=probability<=1:continue
     actual=None
     if result:
      participated=(g['gameId'],pid) in participation or any(code(a.get('team'))==code(p['team']) and name(a.get('name'))==name(p['name']) for a in result.get('playerStats',[]))
      if market=='player_anytime_td':
       scorer=[s for s in result.get('scorers',[]) if code(s.get('team'))==code(p['team']) and name(s.get('name'))==name(p['name'])]
       if len(scorer)==1 and scorer[0].get('touchdowns',0)>0:actual=1
       elif not scorer and result.get('scorersComplete') and participated:actual=0
      elif result.get('touchdownOrder',{}).get('complete') and participated:
       scorer=result['touchdownOrder'].get('first' if market=='player_1st_td' else 'last');actual=int(bool(scorer and code(scorer.get('team'))==code(p['team']) and name(scorer.get('name'))==name(p['name'])))
     put({**game_meta(g['gameId']),'id':'published:'+g['gameId']+':'+pid+':'+market,'scope':'published','sourceCommit':g.get('sourceCommit'),'market':market,'type':'probability','entity':p['name'],'playerId':pid,'position':p.get('position') or profiles.get(pid,{}).get('position'),'team':p['team'],'kickoff':g['kickoff'],'issuedAt':issued,'projected':probability,'actual':actual,'status':'scored' if actual is not None else 'awaiting_scoring' if result else 'pending','actualSource':'ESPN final scoring summary' if actual is not None else None})
 # Retain historical sportsbook research cohorts, separate from all-player forecast evidence.
 bets={r['id']:r for r in previous.get('comparisons',[])}
 for r in legacy.get('rows',[]):
  value={**r,'cohort':'Fixed-rule archived research selection'}
  if r.get('market')=='touchdown' and r.get('status')=='loss':
   result=final_result(r,results)
   observed=(r['gameId'],r.get('playerId')) in participation or result and any(code(a.get('team'))==code(r.get('team')) and name(a.get('name'))==name(r['pick']) for a in result.get('playerStats',[]))
   if not observed:value.update(status='ungraded',review='Participation not confirmed')
  bets[r['id']]=value
 for r in rows.values():
  b=r.get('benchmark');actual=r.get('actual')
  if r['scope']!='published' or r['type']!='continuous' or not b or not finite(b.get('line')):continue
  side='Over' if r['projected']>b['line'] else 'Under' if r['projected']<b['line'] else None
  status='pending' if not finite(actual) else 'ungraded' if not side else 'push' if actual==b['line'] else 'win' if (actual>b['line'])==(side=='Over') else 'loss'
  bets[r['id']]={**r,'pick':(side+' '+str(b['line'])) if side else 'No lean','line':b['line'],'book':b.get('book'),'status':status,'cohort':'First recorded pregame player-prop line'}
 return {'schemaVersion':2,'generatedAt':now,'markets':metadata(),'forecasts':sorted(rows.values(),key=lambda r:(r['season'],r['week'],r['id']),reverse=True),'comparisons':list(bets.values()),'methodology':['Player-stat archives retain original public Git commit times. Older game/TD archives retain model-issue timestamps and are snapshot research, not independently verified wager logs.','Published history and reconstructed walk-forward tests are separate cohorts. Older unavailable history is not invented.','Combined totals sum matching component means from the same issue time; prediction intervals are not added because their dependence is unknown.','Continuous error is measured in each stat’s native units; different stats are never pooled into one MAE. Bias is projected minus actual.','Baseline skill compares the model and rolling baseline on exactly the same rows. Missing baseline values remain unavailable.','80% interval coverage measures distribution calibration, not a bet win rate.','Moneyline calibration uses home-win probability conditional on no tie; tied games are not graded as binary wins/losses. TD probabilities include every archived player, not only successful picks.','First/last TD order is graded only when every scoring touchdown is resolved to a scorer. Passing TDs do not count as a QB anytime TD.','Official weekly player statistics are preferred; unresolved outcomes may use explicitly listed final ESPN box scores. Missing player stats are not filled with zero.','Sportsbook results use separately recorded lines and deterministic selections, not executed wagers. No ROI, closing-line value, or profitability proof is claimed.']}

def update_performance(output=Path('data'),now=None):
 output=Path(output);stamp=now or dt.datetime.now(dt.timezone.utc).isoformat()
 previous=read(output/'model-performance.json')
 if 'forecasts' not in previous:
  previous={**previous,'forecasts':[],'comparisons':[]}
  for shard in [*previous.get('forecastFiles',[]),*previous.get('comparisonFiles',[])]:
   stored=read(output/shard['path']);previous['forecasts'].extend(stored.get('forecasts',[]));previous['comparisons'].extend(stored.get('comparisons',[]))
 value=build_performance(previous,read(output/'projection-results.json'),read(output/'oos-predictions.json',[]),read(output/'latest.json'),read(output/'game-projection-history.json'),[read(output/'touchdown-pregame-archive.json'),read(output/'touchdown-research.json'),read(output/'performance-td-seed.json')],read(output/'public-game-odds.json'),read(output/'model-record.json'),stamp)
 archive=output/'performance';archive.mkdir(parents=True,exist_ok=True)
 manifest={k:v for k,v in value.items() if k not in ['forecasts','comparisons']};manifest.update(schemaVersion=3,forecastFiles=[],comparisonFiles=[])
 groups={}
 for r in value['forecasts']:groups.setdefault((r['season'],r['scope']),[]).append(r)
 for (season,scope),rows in groups.items():
  path=f'performance/{season}-{scope}.json';(output/path).write_text(json.dumps({'forecasts':rows},separators=(',',':'),allow_nan=False));manifest['forecastFiles'].append({'season':season,'scope':scope,'path':path,'rows':len(rows),'scored':sum(finite(r.get('actual')) for r in rows)})
 groups={}
 for r in value['comparisons']:groups.setdefault(r['season'],[]).append(r)
 for season,rows in groups.items():
  path=f'performance/{season}-comparisons.json';(output/path).write_text(json.dumps({'comparisons':rows},separators=(',',':'),allow_nan=False));manifest['comparisonFiles'].append({'season':season,'path':path,'rows':len(rows)})
 (output/'model-performance.json').write_text(json.dumps(manifest,separators=(',',':'),allow_nan=False));return manifest
if __name__=='__main__':update_performance()
