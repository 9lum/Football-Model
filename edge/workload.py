"""Same-team conditional workload allocation. Expected lineup scenarios, not validated edges."""
import copy
import hashlib
import math
from datetime import datetime,timezone
import numpy as np
CHANNELS={'carries':(['RB','QB'],'team_carries_last6',4),'targets':(['RB','WR','TE'],'team_targets_last6',2),'attempts':(['QB'],'team_attempts_last6',10)}
MARKETS={'carries':['player_rush_attempts','player_rush_yds','player_rush_tds'],'targets':['player_receptions','player_reception_yds','player_reception_tds'],'attempts':['player_pass_attempts','player_pass_completions','player_pass_yds','player_pass_tds','player_pass_interceptions']}
TARGETS={'player_rush_attempts':'carries','player_rush_yds':'rushing_yards','player_rush_tds':'rushing_tds','player_receptions':'receptions','player_reception_yds':'receiving_yards','player_reception_tds':'receiving_tds','player_pass_attempts':'attempts','player_pass_completions':'completions','player_pass_yds':'passing_yards','player_pass_tds':'passing_tds','player_pass_interceptions':'passing_interceptions'}
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def stamp(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).timestamp()
 except (ValueError,TypeError):return float('nan')
def mean(values):
 values=[v for v in values if finite(v)];return float(np.mean(values)) if values else None

def build_context(bundle,health,now=None,draws=512):
 now=now or datetime.now(timezone.utc);clock=now.timestamp();season=bundle['season'];profiles={p['playerId']:p for p in bundle.get('players',[])};roles={}
 for r in health.get('roster',[]):
  old=roles.get(r['playerId'])
  if not old or r.get('rank',99)<old.get('rank',99):roles[r['playerId']]=r
 injuries=health.get('injuries',{});base={f['playerId']:f for f in bundle.get('forecasts',[])};games={}
 for f in base.values():
  if int(f['gameId'].split('_')[1])==health['week'] and stamp(f['kickoff'])>clock:games[(f['team'],f['gameId'])]=f
 entries={};new=[];groups=[];skipped=[]
 def history(pid,team,cutoff):return {g['gameId']:g for g in profiles.get(pid,{}).get('history',[]) if g.get('team')==team and g.get('season')==season and stamp(g.get('kickoff'))<cutoff}
 for (team,game_id),game in games.items():
  cutoff=min(clock,stamp(game['kickoff']));team_rows={}
  for p in profiles.values():
   for gid,g in history(p['playerId'],team,cutoff).items():team_rows.setdefault(gid,{})[p['playerId']]=g
  bad=set(bundle.get('dataQuality',{}).get('completedScheduleGamesWithoutPlayerRows',[]));ids=sorted([gid for gid in team_rows if gid not in bad],key=lambda gid:stamp(next(iter(team_rows[gid].values()))['kickoff']))
  if len(ids)<3:continue
  recent=ids[-3:]
  for channel,(positions,budget_key,threshold) in CHANNELS.items():
   returning=[]
   for pid,r in roles.items():
    if r.get('team')!=team or r.get('position') not in positions or not r.get('fresh') or (not r.get('listedStarter') and not any(x.get('playerId')==pid for x in health.get('returnReports',{}).get('reports',[]))):continue
    h=injuries.get(pid,{})
    reports=[x for x in health.get('returnReports',{}).get('reports',[]) if x.get('playerId')==pid]
    conditional=bool(not r.get('expectedStarter') or h.get('ruledOut') or h.get('status') in ['OUT','IR','INACTIVE','DOUBTFUL','QUESTIONABLE'])
    if conditional and not reports and h.get('status')!='QUESTIONABLE':continue
    own=history(pid,team,cutoff);active=[gid for gid in ids if finite(own.get(gid,{}).get(channel)) and own[gid][channel]>0]
    missing=[gid for gid in recent if gid not in own]
    if len(active)<2 or not missing:continue
    established=mean([own[gid][channel] for gid in active[-6:]])
    if established is None or established<threshold:continue
    # Current listed role is an expectation; secondary Active is not an official inactive-list confirmation.
    returning.append({'playerId':pid,'name':r['name'],'position':r['position'],'status':h.get('status','NOT_LISTED'),'confirmed':bool(h.get('confirmed') and h.get('status')=='ACTIVE'),'scenarioOnly':conditional,'reports':reports,'uncertain':bool(h.get('reviewRequired') or h.get('conflict') or h.get('status')=='QUESTIONABLE'),'missingRecentTeamGames':missing,'activeGames':active,'source':r.get('source'),'injurySources':list(dict.fromkeys(s.get('source') for s in h.get('sources',[]) if s.get('source')))})
   if not returning:continue
   scenario_only=any(p['scenarioOnly'] for p in returning)
   members=[]
   for pid,p in profiles.items():
    r=roles.get(pid,{});h=injuries.get(pid,{})
    if r.get('team',p.get('team'))!=team or r.get('position',p.get('position')) not in positions or ((h.get('ruledOut') or h.get('status') in ['OUT','INACTIVE','IR']) and not (scenario_only and any(x['playerId']==pid for x in returning))):continue
    if health.get('currentTeams',{}).get(pid,team)!=team:continue
    f=base.get(pid)
    if f and (f['team']!=team or f['gameId']!=game_id):continue
    if not f and not any(x['playerId']==pid for x in returning):continue
    own=history(pid,team,cutoff)
    if len(own)<2:continue
    if not f:
     f={k:game[k] for k in ['team','opponent','homeTeam','awayTeam','gameId','kickoff']};f.update(playerId=pid,name=p['name'],position=r.get('position',p['position']),marketSamples={},features={},forecastKind='returning_player_workload_scenario',historyGames=len(own),availabilityConfirmed=False)
     records=[own[gid] for gid in ids if gid in own][-6:];rng=np.random.default_rng(int(hashlib.sha256((pid+game_id).encode()).hexdigest()[:8],16))
     for kind,(pos,_,_) in CHANNELS.items():
      if f['position'] not in pos:continue
      denom=mean([g.get(kind) for g in records]);f['features'][kind+'_last3']=mean([g.get(kind) for g in records[-3:]]) or 0
      if not denom or denom<=0:continue
      indices=rng.integers(0,len(records),draws)
      for market in MARKETS[kind]:
       target=TARGETS[market];values=[records[i].get(target) for i in indices]
       if not all(finite(v) for v in values):continue
       f['marketSamples'][market]={'values':values,'mean':float(np.mean(values)),'p10':float(np.quantile(values,.1)),'p90':float(np.quantile(values,.9)),'target':target,'family':{'carries':'rushing','targets':'receiving','attempts':'passing'}[kind],'validationPassed':False,'label':bundle.get('marketConfig',{}).get(market,{}).get('label',target)}
     if not f['marketSamples']:continue
     base[pid]=f
     if not scenario_only and not h.get('ruledOut') and h.get('status') not in ['OUT','IR','INACTIVE','DOUBTFUL']:new.append(f)
    if not any(m in f.get('marketSamples',{}) for m in MARKETS[channel]):continue
    # Pair comparisons use only actual recorded player rows, never DNPs filled with zero.
    peers=sorted(returning,key=lambda x:(x['position']!=f['position'],x['playerId']!=pid,-len(x['activeGames'])))
    peer=peers[0];shared=[gid for gid in ids if gid in own and gid in peer['activeGames'] and finite(own[gid].get(channel))]
    if len(shared)<2:skipped.append({'playerId':pid,'gameId':game_id,'channel':channel,'reason':'Fewer than two recorded shared-role games'});continue
    def total(gid):return sum(g.get(channel,0) for g in team_rows[gid].values() if finite(g.get(channel)))
    paired=[gid for gid in ids[-12:] if gid in own and finite(own[gid].get(channel)) and total(gid)>0]
    shared=[gid for gid in shared[-8:] if total(gid)>0]
    if not paired or len(shared)<2:continue
    prior=sum(own[g][channel] for g in paired)/sum(total(g) for g in paired);opportunities=sum(total(g) for g in shared);pseudo=2*(mean([total(g) for g in shared]) or 1)
    share=(sum(own[g][channel] for g in shared)+pseudo*prior)/(opportunities+pseudo)
    baseline=f.get('features',{}).get(channel+'_last3');baseline=baseline if finite(baseline) and baseline>0 else mean([own[g].get(channel) for g in paired[-3:]])
    if baseline is None or baseline<=0:continue
    if channel=='attempts' and not r.get('expectedStarter'):share=0
    members.append({'pid':pid,'forecast':f,'share':max(0,share),'baseline':baseline,'sharedGames':len(shared),'opportunities':opportunities,'returning':peer})
   if not members:continue
   totals=[sum(g.get(channel,0) for g in team_rows[gid].values() if finite(g.get(channel))) for gid in ids[-6:]];totals=[t for t in totals if t>0]
   if not totals:continue
   # Reserve the observed share of team volume attributable to players without an eligible forecast.
   denominator=sum(totals);represented=sum(sum(g.get(channel,0) for pid,g in team_rows[gid].items() if (pid in {m['pid'] for m in members} or injuries.get(pid,{}).get('ruledOut')) and profiles.get(pid,{}).get('position') in positions and finite(g.get(channel))) for gid in ids[-6:]);represented=min(1,max(0,represented/denominator))
   weights=np.array([m['share'] for m in members]);mass=weights.sum()
   if mass<=0:continue
   weights/=mass;confidence=max(2,min(m['opportunities'] for m in members));active_weights=weights>0;alpha=weights[active_weights]*confidence;rng=np.random.default_rng(int(hashlib.sha256((team+game_id+channel).encode()).hexdigest()[:8],16));probabilities=np.zeros((draws,len(weights)));probabilities[:,active_weights]=rng.dirichlet(alpha,draws);budget=np.array([max(0,round(t*represented)) for t in rng.choice(totals,draws)]);allocated=np.array([rng.multinomial(int(n),p) for n,p in zip(budget,probabilities)])
   for j,m in enumerate(members):
    f=m['forecast'];entry=entries.setdefault(m['pid'],{'playerId':m['pid'],'name':f['name'],'team':team,'gameId':game_id,'kickoff':game['kickoff'],'channels':{},'returningPlayers':[],'researchOnly':True})
    actor={k:v for k,v in m['returning'].items() if k!='activeGames'}
    if not any(p['playerId']==actor['playerId'] for p in entry['returningPlayers']):entry['returningPlayers'].append(actor)
    counts=allocated[:,j].tolist();entry['channels'][channel]={'scenarioOnly':scenario_only,'baseline':m['baseline'],'allocated':counts,'expected':float(np.mean(counts)),'factor':float(np.mean(counts))/m['baseline'],'sharedGames':m['sharedGames'],'scope':'Observed shared-role usage, shrunk toward own same-team usage. Team opportunities resampled from six prior published games; model per-opportunity efficiency retained.'}
   groups.append({'team':team,'gameId':game_id,'channel':channel,'returningPlayers':[p['name'] for p in returning],'participants':[m['pid'] for m in members],'budgetMean':float(budget.mean()),'allocatedMean':float(allocated.sum(axis=1).mean()),'budgetMax':int(budget.max()),'representedHistoricalShare':represented,'pairedSupportMinimum':min(m['sharedGames'] for m in members)})
 return {'schemaVersion':1,'generatedAt':now.isoformat(),'modelGeneratedAt':bundle['generatedAt'],'season':season,'week':health['week'],'players':entries,'newForecasts':new,'groups':groups,'skipped':skipped,'validationPassed':False,'methodology':'Conditional expected-lineup research allocation, not a validated improvement to the forest. No arbitrary play probability for questionable returns. Historical coappearance is descriptive, not proof of causal injury effects. Missing player rows are not zero-filled as game outcomes.','scope':'Current-team QB/RB/WR/TE opportunities. Archived actual statistics and sportsbook quotes are never rewritten.'}
