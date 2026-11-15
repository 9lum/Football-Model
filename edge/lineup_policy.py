"""Invalidate stale-role future offers without treating unknown participation as a zero outcome."""
import copy,datetime as dt,math
UTC=dt.timezone.utc
def stamp(v):
 try:return dt.datetime.fromisoformat(str(v).replace('Z','+00:00')).timestamp()
 except (ValueError,TypeError):return float('nan')
def touches(row):
 if not row:return None
 values=[row.get(k) for k in ['carries','targets']]
 return sum(v for v in values if isinstance(v,(int,float)) and math.isfinite(v)) if any(isinstance(v,(int,float)) and math.isfinite(v) for v in values) else None

def build_lineup_policy(bundle,health,now=None):
 now=now or dt.datetime.now(UTC);clock=now.timestamp();age=clock-stamp(health.get('generatedAt'));entries={}
 if health.get('season')!=bundle.get('season') or not 0<=age<=7200:return {'version':1,'generatedAt':now.isoformat(),'players':{},'status':'stale_or_unavailable'}
 profiles={p['playerId']:p for p in bundle.get('players',[])};roles={r['playerId']:r for r in health.get('roster',[])};injuries=health.get('injuries',{});bad=set(bundle.get('dataQuality',{}).get('completedScheduleGamesWithoutPlayerRows',[]))
 for f in bundle.get('forecasts',[]):
  pid=f['playerId'];r=roles.get(pid,{});h=injuries.get(pid,{})
  if stamp(f['kickoff'])<=clock or int(f['gameId'].split('_')[1])!=health.get('week'):continue
  reason=None;scope=h.get('week',health.get('week'))==health.get('week') and not h.get('scopeMismatch')
  if scope and not h.get('conflict') and (h.get('ruledOut') or h.get('status') in ['OUT','IR','INACTIVE','SUSPENDED','PUP','NFI'] and (h.get('confirmed') or h.get('selectionTrusted'))):reason='Current availability report rules this player out; no participation-conditional touchdown offer.'
  if r.get('fresh') and r.get('team')!=f['team']:reason='Current roster team differs from this forecast.'
  evidence={}
  if not reason and r.get('fresh') and r.get('position')=='RB' and r.get('rank',0)>=3 and not r.get('expectedStarter'):
   team=f['team'];histories={p:{g['gameId']:g for g in profile.get('history',[]) if g.get('season')==bundle['season'] and g.get('team')==team and stamp(g.get('kickoff'))<clock and g.get('gameId') not in bad} for p,profile in profiles.items()}
   games={gid:stamp(g['kickoff']) for own in histories.values() for gid,g in own.items()};recent=sorted(games,key=games.get)[-2:]
   leaders=[x for x in roles.values() if x.get('team')==team and x.get('position')=='RB' and x.get('fresh') and x.get('expectedStarter') and not injuries.get(x['playerId'],{}).get('ruledOut')]
   if len(recent)==2 and leaders and all((touches(histories.get(pid,{}).get(g)) or 0)==0 for g in recent) and any(all((touches(histories.get(x['playerId'],{}).get(g)) or 0)>0 for g in recent) for x in leaders):
    reason='Deep-backup RB depth role with no recorded carries or targets in the last two published team games while the current starter had offensive opportunities. Historical starter-like usage is not a supported upcoming role.'
    evidence={'depthRank':r['rank'],'recentTeamGames':recent,'recordedOpportunities':[touches(histories.get(pid,{}).get(g)) for g in recent],'starterIds':[x['playerId'] for x in leaders]}
  if reason:entries[pid]={'eligible':False,'gameId':f['gameId'],'team':f['team'],'reason':reason,'evidence':evidence,'policy':'current_lineup_v1'}
 return {'version':1,'generatedAt':now.isoformat(),'modelGeneratedAt':bundle.get('generatedAt'),'players':entries,'status':'current','scope':'Future forecast eligibility only. Missing rows are not actual zeros. No scoring probability or void-bet outcome is invented.'}

def apply_touchdown_lineup(report,policy,now=None):
 if not report:return report
 now=now or dt.datetime.now(UTC);clock=now.timestamp();result=copy.deepcopy(report);blocked={}
 for pid,decision in policy.get('players',{}).items():
  e=result.get('allPlayerOdds',{}).get(pid,{})
  if e.get('gameId')!=decision['gameId'] or stamp(e.get('kickoff'))<=clock:continue
  blocked[pid]=decision;e.update(status='unavailable',markets={},reason=decision['reason'],lineupPolicy=decision)
 for g in result.get('games',[]):
  if stamp(g.get('kickoff'))<=clock:continue
  affected={pid:d for pid,d in policy.get('players',{}).items() if d.get('gameId')==g['gameId']}
  for key in ['players','candidates']:g[key]=[p for p in g.get(key,[]) if p['playerId'] not in affected]
  if affected:g['lineupExclusions']=list(affected.values())
 result['lineupPolicyAppliedAt']=policy.get('generatedAt');return result
