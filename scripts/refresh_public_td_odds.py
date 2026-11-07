"""Credential-free, indicative TD scorer prices from DraftKings' public editorial table."""
import datetime as dt,html,json,re
from pathlib import Path
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
FULL_NAMES={'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens', 'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears', 'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys', 'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers', 'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars', 'KC': 'Kansas City Chiefs', 'LAC': 'Los Angeles Chargers', 'LAR': 'Los Angeles Rams', 'LV': 'Las Vegas Raiders', 'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings', 'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants', 'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers', 'SEA': 'Seattle Seahawks', 'SF': 'San Francisco 49ers', 'TB': 'Tampa Bay Buccaneers', 'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders'}
URL='https://dknetwork.draftkings.com/draftkings-sportsbook-player-props/?tb_eg=88808&tb_edate=n7days&tb_view=2'
def clean(value):return re.sub('[^a-z0-9]','',value.lower())
def parse(raw,bundle,now):
    matches={};profiles=bundle.get('players',[])
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw,re.S):
        cells=[html.unescape(re.sub('<[^>]+>',' ',c)).strip() for c in re.findall(r'<td\b[^>]*>(.*?)</td>',tr,re.S)]
        if len(cells)!=5 or cells[2] not in ['Anytime TD Scorer','2+ TDs']:continue
        matchup,date,label,name,price=cells;href=re.search(r'href=[\"\'](https://sportsbook\.draftkings\.com/[^\"\']+)',tr)
        if not href:continue
        try:price=int(price.replace('−','-').replace(' ','').replace(',',''))
        except ValueError:continue
        if abs(price)<100:continue
        # Resolve against a unique scheduled matchup, player and Eastern local date/time.
        candidates=[]
        for f in bundle.get('forecasts',[]):
            kickoff=dt.datetime.fromisoformat(f['kickoff'].replace('Z','+00:00'))
            if not now<kickoff<=now+dt.timedelta(days=8) or clean(f['name'])!=clean(name):continue
            local=kickoff.astimezone(ZoneInfo('America/New_York'))
            expected=f'{local.month}/{local.day}, '+local.strftime('%I:%M%p')
            if re.sub(r'\s+','',date).lower()!=re.sub(r'\s+','',expected).lower():continue
            # Both team abbreviations are checked; LA/NY aliases are paired with nickname.
            aliases={'NYJ':'NY Jets','NYG':'NY Giants','LAR':'LA Rams','LAC':'LA Chargers','KC':'KC Chiefs','GB':'GB Packers','NE':'NE Patriots','TB':'TB Buccaneers','SF':'SF 49ers'}
            def team_label(team):return aliases.get(team,team+' '+FULL_NAMES[team].split()[-1])
            if clean(matchup)!=clean(team_label(f['awayTeam'])+' @ '+team_label(f['homeTeam'])):continue
            candidates.append(f)
        if len(candidates)!=1:continue
        f=candidates[0];key='player_anytime_td' if label=='Anytime TD Scorer' else 'player_tds_over';line=.5 if key=='player_anytime_td' else 1.5
        item=matches.setdefault(f['gameId'],{'id':'public-dk-'+f['gameId'],'gameId':f['gameId'],'home_team':FULL_NAMES[f['homeTeam']],'away_team':FULL_NAMES[f['awayTeam']],'commence_time':f['kickoff'],'bookmakers':[{'key':'draftkings','title':'DraftKings','markets':[]}]})
        market=next((m for m in item['bookmakers'][0]['markets'] if m['key']==key),None)
        if market is None:market={'key':key,'source':URL,'sourceKind':'public_web','observedAt':now.isoformat(),'last_update':None,'outcomes':[]};item['bookmakers'][0]['markets'].append(market)
        outcome={'name':'Yes','description':f['name'],'point':line,'price':price,'link':html.unescape(href[1])}
        if not any(o['description']==outcome['description'] for o in market['outcomes']):market['outcomes'].append(outcome)
    return list(matches.values())
def collect(output=Path('data'),now=None):
    now=now or dt.datetime.now(dt.timezone.utc);path=output/'public-td-odds.json';report={'generatedAt':now.isoformat(),'source':URL,'status':'unavailable','data':[],'scope':'Public DraftKings TD scorer table: 1+ and 2+ TDs scored, not separate rushing/receiving TDs. Passing TDs excluded; scorer rules may include return TDs. Indicative web snapshot, not a verified executable offer. Source quote update time is not supplied.'}
    try:
        with urlopen(Request(URL,headers={'User-Agent':'NFLResearch/1.0'}),timeout=25) as response:raw=response.read().decode()
        report['data']=parse(raw,json.loads((output/'latest.json').read_text()),now);report['status']='ok' if report['data'] else 'no_matched_prices'
    except Exception as e:
        report['error']=type(e).__name__
        if path.exists():report['data']=json.loads(path.read_text()).get('data',[])
    report['quoteCount']=sum(len(m['outcomes']) for e in report['data'] for b in e['bookmakers'] for m in b['markets']);path.write_text(json.dumps(report,separators=(',',':')));print(json.dumps({k:v for k,v in report.items() if k!='data'}));return report
if __name__=='__main__':collect()
