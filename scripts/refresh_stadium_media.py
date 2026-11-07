"""Cache ESPN's published venue images; no generated image is called a venue photo."""
import datetime as dt
import json
import re
from html import unescape
from urllib.parse import quote,urlparse,unquote
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from intelligence.providers import request_json
ROOT=Path(__file__).resolve().parents[1]
def run():
    feed=json.loads((ROOT/'data/stadium-weather.json').read_text());path=ROOT/'data/stadium-media.json';stadiums={}
    try:stadiums=json.loads(path.read_text()).get('stadiums',{})
    except (OSError,ValueError):pass
    wanted={}
    for game in feed['games']:
        if game['stadium'] not in stadiums and str(game.get('espnId','')).isdigit():wanted.setdefault(game['stadium'],game)
    def fetch(item):
        name,game=item
        try:
            data=request_json('https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary',{'event':game['espnId']});venue=data.get('gameInfo',{}).get('venue',{});photos=venue.get('images',[])
            photo=next((p for p in photos if 'interior' in p.get('rel',[])),photos[0] if photos else None)
            if photo and str(photo.get('href','')).startswith('https://a.espncdn.com/i/venues/'):
                return name,{'url':photo['href'],'alt':venue.get('fullName',name)+' · ESPN venue photograph','source':'https://www.espn.com/nfl/game/_/gameId/'+game['espnId'],'credit':'ESPN venue imagery','retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat()}
        except Exception:pass
        # The neutral Madrid venue does not publish an ESPN image.
        if name.lower() in ['bernabeu','bernabéu']:
            try:
                summary=request_json('https://en.wikipedia.org/api/rest_v1/page/summary/'+quote('Santiago_Bernabéu_Stadium'))
                image=summary.get('thumbnail',{}).get('source','')
                if urlparse(image).hostname not in ['thumb.wikimedia.org','upload.wikimedia.org']:return name,None
                filename=unquote(urlparse(image).path.split('/')[-2])
                metadata=request_json('https://commons.wikimedia.org/w/api.php',{'action':'query','format':'json','prop':'imageinfo','iiprop':'extmetadata','titles':'File:'+filename})
                info=next(iter(metadata['query']['pages'].values()))['imageinfo'][0]['extmetadata']
                clean=lambda key:unescape(re.sub('<[^>]+>','',str(info.get(key,{}).get('value',''))))
                licence=clean('LicenseShortName');artist=clean('Artist')
                if not licence:return name,None
                return name,{'url':image,'alt':name+' · Wikimedia Commons photograph','source':'https://commons.wikimedia.org/wiki/File:'+quote(filename),'credit':(artist+' · '+licence+' · Wikimedia Commons').strip(' ·'),'retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat()}
            except Exception:pass
        return name,None
    with ThreadPoolExecutor(max_workers=4) as executor:
        for name,photo in executor.map(fetch,wanted.items()):
            if photo:stadiums[name]=photo
    path.write_text(json.dumps({'stadiums':stadiums,'scope':'Public ESPN venue images, with a credited Wikimedia Commons fallback for Madrid; cached to avoid repeated provider calls.'},separators=(',',':')));print(f'Cached {len(stadiums)} stadium photographs')
if __name__=='__main__':run()
