"""Quota-aware ATTD snapshots. Secrets remain in Actions; old timestamps are preserved."""
import datetime as dt
import json,math,os
from pathlib import Path
from urllib.parse import quote
from scripts.refresh_odds import fetch,read,number,ProviderError

def collect(output=Path('data'),key=None,now=None):
 now=now or dt.datetime.now(dt.timezone.utc);output.mkdir(exist_ok=True,parents=True);previous=read(output/'attd-odds.json',{});prior={e['id']:e for e in previous.get('data',[]) if e.get('id')};report={'generatedAt':now.isoformat(),'source':'The Odds API','market':'player_anytime_td','status':'unavailable','errors':[],'data':[],'cadence':'Checked every six hours. Initial coverage across upcoming games; subsequent requests rotate within the shared monthly credit allowance.'}
 try:
  key=key or os.environ.get('ODDS_API_KEY')
  if not key:raise ProviderError('missing_secret')
  events,quota=fetch('events',key);remaining=number(quota.get('remaining'),0);eligible=[e for e in events if now<dt.datetime.fromisoformat(e['commence_time'].replace('Z','+00:00'))<=now+dt.timedelta(days=8)];eligible.sort(key=lambda e:(prior.get(e['id'],{}).get('collectedAt',''),e['commence_time']))
  # Initial all-game coverage costs two credits/event, then ~25% of remaining monthly credits.
  days=max(1,32-now.day);budget=min(32,max(0,remaining-100)) if not prior else min(8,max(0,math.floor(remaining*.25/(days*4))))
  override=os.environ.get('ATTD_REFRESH_CREDIT_BUDGET');budget=min(remaining,number(override,budget)) if override else budget;spent=0;fresh=0
  for event in eligible:
   if spent+2>budget:break
   try:
    value,q=fetch('events/'+quote(event['id'],safe='')+'/odds',key,regions='us,us2',markets='player_anytime_td',oddsFormat='american');spent+=number(q.get('last'),2);report['quota']=q
    if not isinstance(value.get('bookmakers'),list):raise ProviderError('schema')
    value['collectedAt']=now.isoformat();prior[event['id']]=value;fresh+=1
   except ProviderError as error:
    spent+=2;report['errors'].append({'eventId':event['id'],'code':error.status})
    if error.status in [401,403,429]:break
  valid={e['id'] for e in eligible};report.update(data=[e for k,e in prior.items() if k in valid],status='ok' if fresh else 'quota_wait',freshEvents=fresh,eligibleEvents=len(eligible),creditBudget=budget,estimatedCreditsUsed=spent)
 except ProviderError as error:report['errors'].append({'code':error.status});report['data']=list(prior.values())
 report['pricedEvents']=sum(any(m.get('key')=='player_anytime_td' and m.get('outcomes') for b in e.get('bookmakers',[]) for m in b.get('markets',[])) for e in report['data'])
 report['quoteCount']=sum(len(m.get('outcomes',[])) for e in report['data'] for b in e.get('bookmakers',[]) for m in b.get('markets',[]) if m.get('key')=='player_anytime_td')
 (output/'attd-odds.json').write_text(json.dumps(report,separators=(',',':')));print(json.dumps({k:v for k,v in report.items() if k!='data'}));return report
if __name__=='__main__':collect()
