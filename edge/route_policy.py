"""Prequential 0/5/10/15% route-depth adjustments learned only from earlier completed weeks."""
import numpy as np
COEFFICIENTS=[0.,.05,.10,.15]
TARGETS=['targets','receptions','receiving_yards']
def finite(x):return isinstance(x,(int,float,np.floating)) and np.isfinite(x)
class RoutePolicy:
 def __init__(self,complete_weeks):self.complete_weeks=set(complete_weeks)
 def select(self,previous,week):
  records=[r for r in previous if r.get('week',week)>=week-8 and r.get('week',week)<week and r.get('week') in self.complete_weeks and r.get('routeCandidates')]
  n=len(records);games=len({r['game_id'] for r in records})
  if n<200 or games<30:return {'volume':.05,'yards':.05,'n':n,'games':games,'trainedThroughWeek':max([r['week'] for r in records],default=None),'status':'Research warm-up; not independently validated'}
  def choose(targets):
   scores=[]
   for index,coefficient in enumerate(COEFFICIENTS):
    normalized=[]
    for target in targets:
     matched=[r for r in records if target in r and target in r['routeCandidates']]
     if not matched:continue
     actual=np.asarray([r[target]['actual'] for r in matched]);base=np.asarray([r['routeCandidates'][target][0] for r in matched]);candidate=np.asarray([r['routeCandidates'][target][index] for r in matched])
     normalized.append(np.mean(np.abs(candidate-actual))/max(np.mean(np.abs(base-actual)),.1))
    scores.append(float(np.mean(normalized)) if normalized else 1.)
   best=int(np.argmin(scores));return COEFFICIENTS[best] if scores[best]<scores[0]*.99 else 0.
  return {'volume':choose(['targets','receptions']),'yards':choose(['receiving_yards']),'n':n,'games':games,'trainedThroughWeek':max(r['week'] for r in records),'status':'Learned from earlier completed weeks; no guaranteed improvement'}
 def candidates(self,samples,targets,context):
  direction=context.get('direction',0) if context.get('status')=='available' else 0
  return {target:[np.floor(samples[:,targets.index(target)]*(1+direction*c)+(np.arange(len(samples))+.5)/len(samples)) for c in COEFFICIENTS] for target in TARGETS if target in targets}
 def apply(self,test,samples,targets,previous):
  out=samples.copy();metadata=[];week=int(test.week.iloc[0]);policy=self.select(previous,week)
  for j,r in enumerate(test.itertuples()):
   context=getattr(r,'routeContext',{}) or {};available=context.get('status')=='available' and bool(context.get('direction'));candidates=self.candidates(samples[j],targets,context);candidate_means={target:[float(a.mean()) for a in arrays] for target,arrays in candidates.items()}
   coefficients={t:policy['yards'] if t=='receiving_yards' else policy['volume'] for t in TARGETS};direction=context.get('direction',0) if available else 0
   for target,arrays in candidates.items():out[j,:,targets.index(target)]=arrays[COEFFICIENTS.index(coefficients[target])]
   if 'targets' in targets and 'receptions' in targets:out[j,:,targets.index('receptions')]=np.minimum(out[j,:,targets.index('receptions')],out[j,:,targets.index('targets')])
   if 'receiving_tds' in targets and 'receptions' in targets:out[j,:,targets.index('receiving_tds')]=np.minimum(out[j,:,targets.index('receiving_tds')],out[j,:,targets.index('receptions')])
   metadata.append({'routeCandidates':candidate_means if available else None,'routePolicy':policy,'routeFactors':{target:1+direction*c for target,c in coefficients.items()},'routeSignal':context.get('signal',0.)})
  return out,metadata
 def validation(self,details,targets):
  result={}
  for target in targets:
   records=[r for r in details if r.get('week') in self.complete_weeks and r.get('routeCandidates') and target in r and finite(r[target].get('unadjustedMean'))]
   if not records:continue
   base=np.mean([abs(r[target]['unadjustedMean']-r[target]['actual']) for r in records]);adjusted=np.mean([abs(r[target]['mean']-r[target]['actual']) for r in records]);games=len({r['game_id'] for r in records})
   result[target]={'n':len(records),'games':games,'baselineMAE':float(base),'adjustedMAE':float(adjusted),'incrementalPassed':bool(len(records)>=500 and games>=40 and adjusted<base*.99)}
  return result

def rationale(name,opponent,context,policy,factors):
 if context.get('status')!='available':return [f'No route-depth adjustment is applied for {name}: {context.get("reason","published depth/location evidence is unavailable")}.','Baseline projections are retained; absent route concepts or coverage rates are not filled with invented values.']
 profile=context['profile'];shares=profile['depthShares'];man=context.get('manRate');zone=context.get('zoneRate');coverage=f'{man:.0%} man/{zone:.0%} zone' if finite(man) and finite(zone) else 'unavailable man/zone charting'
 evidence=context.get('evidence',[]);region=max(evidence,key=lambda v:v['playerTargetShare']*abs(v['defenseEPA']-v['leagueEPA'])) if evidence else None
 weak=f"{region['region'].replace('_',' ')} allowed {region['defenseEPA']:.2f} EPA per targeted pass versus a {region['leagueEPA']:.2f} prior-season league reference" if region else 'no supported regional weakness is available'
 return [f"{name}'s recent target-depth mix is {shares['short']:.0%} short/{shares['intermediate']:.0%} intermediate/{shares['deep']:.0%} deep against {opponent}'s {coverage}; {weak}.",f"The prior-week policy applies {(factors.get('targets',1)-1):+.0%} to targets/receptions and {(factors.get('receiving_yards',1)-1):+.0%} to yards, using targeted-pass locations as route-profile proxies and avoiding a second man/zone multiplier; {policy['status'].lower()}."]
