"""Bounded public return-report discovery. Search mentions never establish active status."""
import concurrent.futures
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
HANDLES={'rapsheet','adamschefter','tompelissero','mikegarafolo','jjones9','richcimini','fieldyates','diannaespn'}
SIGNAL=re.compile(r'\b(return|returning|returns|activated|activation|practice window|cleared|comeback|expected to play)\b',re.I)
def collect(bundle,health,now,fetch=None):
    """Official RSS plus allowlisted indexed X mentions; cap search requests per refresh."""
    from .availability import TEAM_SITES
    fetch=fetch or (lambda url:urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFLResearch/1.0'}),timeout=10).read())
    profiles=bundle.get('players',[]);clubs={f['team'] for f in bundle.get('forecasts',[]) if int(f['gameId'].split('_')[1])==health['week'] and datetime.fromisoformat(f['kickoff'].replace('Z','+00:00'))>now};reports=[];coverage=[]
    jobs=[('official','https://www.'+TEAM_SITES[t]+'/rss/news',t) for t in sorted(clubs) if t in TEAM_SITES]
    # Public indexing is incomplete; no authenticated or comprehensive X-feed claim.
    query='site:x.com (from:RapSheet OR from:AdamSchefter OR from:TomPelissero) NFL return injury'
    jobs.append(('indexed_x','https://www.bing.com/search?format=rss&q='+urllib.parse.quote(query),None))
    def load(job):
        kind,url,club=job
        try:
            root=ET.fromstring(fetch(url));items=root.findall('.//item');found=[]
            for item in items[:40]:
                title=' '.join((item.findtext('title') or '').split());description=re.sub('<[^>]+>',' ',item.findtext('description') or '');link=item.findtext('link') or '';text=title+' '+description
                if not SIGNAL.search(text):continue
                if kind=='indexed_x':
                    match=re.fullmatch(r'https://(?:www\.)?(?:x.com|twitter.com)/([A-Za-z0-9_]+)/status/(\d+)(?:\?.*)?',link)
                    if not match or match[1].lower() not in HANDLES:continue
                    date=datetime.fromtimestamp(((int(match[2])>>22)+1288834974657)/1000,timezone.utc)
                else:
                    from email.utils import parsedate_to_datetime
                    try:date=parsedate_to_datetime(item.findtext('pubDate') or '')
                    except (ValueError,TypeError):continue
                    if date.tzinfo is None:continue
                    if urllib.parse.urlparse(link).hostname not in {TEAM_SITES[club],'www.'+TEAM_SITES[club]}:continue
                if not 0<=(now-date).total_seconds()<=7*86400:continue
                for p in profiles:
                    if club and p.get('team')!=club:continue
                    name_pattern=r'(?<!\w)'+re.escape(p['name'])+r'(?!\w)'
                    sentences=re.split(r'[.!?\n]+',text)
                    if not any(SIGNAL.search(part) and (m:=re.search(name_pattern,part,re.I)) and min(abs(m.start()-signal.start()) for signal in SIGNAL.finditer(part))<=140 for part in sentences):continue
                    found.append({'playerId':p['playerId'],'name':p['name'],'team':p['team'],'source':link,'title':title[:250],'reportedAt':date.isoformat(),'authority':kind,'scenarioOnly':True,'status':'Potential return; activation not inferred'})
            return found,{'source':url,'kind':kind,'status':'checked','matchedReports':len(found)}
        except Exception as e:return [],{'source':url,'kind':kind,'status':'unavailable','error':type(e).__name__}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for found,meta in pool.map(load,jobs):reports.extend(found);coverage.append(meta)
    # Existing secondary injury stories remain evidence with their original timestamps.
    for pid,h in health.get('injuries',{}).items():
        for s in h.get('sources',[]):
            text=' '.join(str(s.get(k,'')) for k in ['injury','returnComment','shortComment','longComment'])
            if SIGNAL.search(text):reports.append({'playerId':pid,'name':h.get('name',pid),'source':s.get('source'),'reportedAt':s.get('reportedAt'),'title':text[:250],'authority':s.get('authority','secondary'),'scenarioOnly':True})
    return {'generatedAt':now.isoformat(),'season':health['season'],'week':health['week'],'reports':reports,'coverage':coverage,'limitations':'Public X indexing is incomplete. Search snippets and return-to-practice reports are conditional evidence, never an official activation or a numeric probability of playing.'}
