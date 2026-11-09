"""Explicit ESPN box-score fields; absent statistics are never inferred as zero."""
from scripts.game_market_history import finite
MAP={'receiving':{'receivingYards':'receiving_yards','receptions':'receptions','receivingTouchdowns':'receiving_tds','receivingTargets':'targets'},'rushing':{'rushingYards':'rushing_yards','rushingAttempts':'carries','rushingTouchdowns':'rushing_tds'},'passing':{'passingYards':'passing_yards','passingTouchdowns':'passing_tds','interceptions':'passing_interceptions'}}
def number(v):
 try:
  value=float(v);return value if finite(value) else None
 except (ValueError,TypeError):return None

def player_stats(summary):
 result={}
 for team in summary.get('boxscore',{}).get('players',[]):
  club=team.get('team',{}).get('displayName')
  for group in team.get('statistics',[]):
   kind=group.get('name');keys=group.get('keys',[])
   if kind not in MAP:continue
   for row in group.get('athletes',[]):
    a=row.get('athlete',{});values=dict(zip(keys,row.get('stats',[])))
    if not a.get('id') or not club:continue
    out=result.setdefault((club,a['id']),{'espnId':str(a['id']),'name':a.get('displayName'),'team':club,'stats':{}})
    for source,target in MAP[kind].items():
     value=number(values.get(source))
     if value is not None:out['stats'][target]=value
    if kind=='passing':
     pair=str(values.get('completions/passingAttempts','')).split('/')
     if len(pair)==2:
      for target,v in zip(['completions','attempts'],pair):
       value=number(v)
       if value is not None:out['stats'][target]=value
 return list(result.values())

def touchdown_order(summary):
 # Scoring plays are ordered by the provider. Require every TD scorer to match exactly.
 roster={}
 for team in summary.get('boxscore',{}).get('players',[]):
  club=team.get('team',{}).get('displayName')
  for group in team.get('statistics',[]):
   for row in group.get('athletes',[]):
    a=row.get('athlete',{})
    if a.get('displayName'):roster[(club,a['displayName'])]={'name':a['displayName'],'team':club,'espnId':str(a.get('id',''))}
 plays=[p for p in summary.get('scoringPlays',[]) if p.get('scoringType',{}).get('name')=='touchdown']
 order=[]
 for p in plays:
  club=p.get('team',{}).get('displayName');text=p.get('text','')
  matches=[v for (team,n),v in roster.items() if team==club and text.startswith(n+' ')]
  if len(matches)!=1:return {'complete':False}
  order.append(matches[0])
 return {'complete':bool(summary.get('scoringPlays')),'count':len(order),'first':order[0] if order else None,'last':order[-1] if order else None}
