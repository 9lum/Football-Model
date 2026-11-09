"""Expected-lineup research forecasts. Never transfer an injured QB's rushing role."""
import hashlib
import numpy as np
COUNTS={'player_pass_attempts','player_pass_completions','player_pass_tds','player_pass_interceptions','player_rush_attempts','player_rush_tds','player_targets','player_receptions','player_reception_tds'}
TARGETS={'player_pass_yds':'passing_yards','player_pass_attempts':'attempts','player_pass_completions':'completions','player_pass_tds':'passing_tds','player_pass_interceptions':'passing_interceptions','player_rush_attempts':'carries','player_rush_yds':'rushing_yards','player_rush_tds':'rushing_tds','player_targets':'targets','player_receptions':'receptions','player_reception_yds':'receiving_yards','player_reception_tds':'receiving_tds'}
def sample(values,key):
 a=np.asarray(values);return {'values':a.tolist(),'mean':float(a.mean()),'p10':float(np.quantile(a,.1)),'p90':float(np.quantile(a,.9)),'target':TARGETS[key],'family':'passing' if key.startswith('player_pass') else 'rushing' if key.startswith('player_rush') else 'receiving','validationPassed':False,'injuryAdjusted':True,'replacementResearch':True}
def identity(reference,role,kind):
 return {**{k:reference[k] for k in ['team','opponent','homeTeam','awayTeam','gameId','kickoff']},'playerId':role['playerId'],'name':role['name'],'position':role['position'],'features':{k:v for k,v in reference.get('features',{}).items() if k.startswith(('team_','opp_','matchup_')) or k in ['week','home']},'marketSamples':{},'availabilityConfirmed':False,'forecastKind':kind,'likelyToPlay':True,'availabilityReviewRequired':True,'sourceModelGeneratedAt':None,'replacementFor':reference['playerId']}
def qb_forecast(reference,role,scenario,info,rates=None,draws=512):
 rates=rates or {};own=[g for g in info.get('recentStarts',[]) if (g.get('attempts') or 0)>0]
 rng=np.random.default_rng(int(hashlib.sha256((role['playerId']+reference['gameId']).encode()).hexdigest()[:8],16));f=identity(reference,role,'backup_qb_scenario')
 f['historyGames']=info.get('recordedStarts',0);f['historyScope']='Recorded starting-QB games; relief appearances excluded where starter IDs are known'
 team_attempts=reference.get('marketSamples',{}).get('player_pass_attempts',{}).get('values',[])
 # Team play volume and backup production are distinct inputs; passing-yard cohort ratios are not rushing ratios.
 attempts=np.array(team_attempts,dtype=float) if team_attempts else np.array([reference.get('features',{}).get('team_attempts_last6') or 32.])
 team_mean=max(1,float(attempts.mean()));own_mean=float(np.mean([g['attempts'] for g in own])) if own else team_mean;weight=len(own)/(len(own)+5);expected_attempts=weight*own_mean+(1-weight)*team_mean
 attempts=np.maximum(1,np.rint(attempts[np.arange(draws)%len(attempts)]*expected_attempts/team_mean)).astype(int)
 own_attempts=sum(g['attempts'] for g in own)
 def rate(target,default):
  valid=[g for g in own if g.get(target) is not None];total=sum(g['attempts'] for g in valid);return (sum(g[target] for g in valid)+60*default)/(total+60)
 completion_rate=np.clip(rate('completions',rates.get('completionRate',.63)),.1,.95);td_rate=np.clip(rate('passing_tds',rates.get('tdPerAttempt',.04)),0,.3);int_rate=np.clip(rate('passing_interceptions',rates.get('intPerAttempt',.025)),0,.2)
 completions=rng.binomial(attempts,completion_rate);tds=rng.binomial(completions,min(1,td_rate/completion_rate));interceptions=rng.binomial(attempts-completions,min(1,int_rate/max(.01,1-completion_rate)))
 yard_base=reference.get('marketSamples',{}).get('player_pass_yds',{}).get('values',[])
 if not yard_base:return None
 yards=np.asarray(yard_base,dtype=float)[np.arange(draws)%len(yard_base)];yards=np.rint(yards*scenario['backupPassingYards']/max(1,float(yards.mean()))).astype(int)
 values={'player_pass_attempts':attempts,'player_pass_completions':completions,'player_pass_yds':yards,'player_pass_tds':tds,'player_pass_interceptions':interceptions}
 rush=[g for g in own if all(g.get(k) is not None for k in ['carries','rushing_yards','rushing_tds'])]
 if len(rush)>=2:
  picked=rng.integers(0,len(rush),draws)
  for key,target in [('player_rush_attempts','carries'),('player_rush_yds','rushing_yards'),('player_rush_tds','rushing_tds')]:values[key]=np.array([round(rush[i][target]) for i in picked],dtype=int)
  f['features']['carries_last3']=float(np.mean([g['carries'] for g in rush[-3:]]))
 f['features']['attempts_last3']=float(np.mean([g['attempts'] for g in own[-3:]])) if own else expected_attempts
 f['features']['replacement_expected_attempts']=float(attempts.mean());f['features']['replacement_own_start_attempts']=own_attempts
 f['marketSamples']={key:sample(v,key) for key,v in values.items()};f['replacementMethod']='Passing yards: own starts plus experience-matched QB-change cohort. Attempts: team volume plus own starting usage. TD/INT/completions: own rates shrunk to prior-season QB rates. Rushing: own recorded starts only; omitted without support. Unvalidated research scenario.'
 return f

def skill_replacements(bundle,roles,injuries):
 """Promote missing non-QB replacements using their own recorded stat lines, never starter clones."""
 profiles={p['playerId']:p for p in bundle.get('players',[])};out=[];existing={f['playerId'] for f in bundle['forecasts']}
 for r in roles:
  if r['position']=='QB' or not r.get('replacement') or r['playerId'] in existing or injuries.get(r['playerId'],{}).get('ruledOut'):continue
  previous=next((p for p in roles if p['team']==r['team'] and p['position']==r['position'] and p['slot']==r['slot'] and p.get('listedStarter') and p['playerId']!=r['playerId']),None)
  ref=next((f for f in bundle['forecasts'] if previous and f['playerId']==previous['playerId']),None)
  if not ref:continue
  history=[g for g in profiles.get(r['playerId'],{}).get('history',[]) if g.get('team')==r['team'] and str(g.get('kickoff',''))<ref['kickoff']][-9:]
  if len(history)<2:continue
  f=identity(ref,r,'replacement_history_scenario');rng=np.random.default_rng(int(hashlib.sha256((r['playerId']+ref['gameId']).encode()).hexdigest()[:8],16));indices=rng.integers(0,len(history),512)
  for key,target in TARGETS.items():
   if key.startswith('player_pass') or r['position']!='RB' and key.startswith('player_rush'):continue
   if not all(isinstance(g.get(target),(int,float)) and np.isfinite(g[target]) for g in history):continue
   f['marketSamples'][key]=sample([round(history[i][target]) for i in indices],key)
  if not f['marketSamples']:continue
  f['sourceModelGeneratedAt']=bundle['generatedAt'];f['historyGames']=len(history);f['replacementMethod']='Own recent same-team recorded production; starter-role promotion is shown, but no unsupported transfer of the absent player’s full workload. Research scenario pending role-specific validation.';out.append(f)
 return out
