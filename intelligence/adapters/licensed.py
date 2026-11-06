import os
from intelligence.providers import request_json,ProviderError
PROVIDERS={'SportsDataIO':'SPORTSDATAIO','PFF':'PFF','Sportradar':'SPORTRADAR','NFL tracking':'NFL_TRACKING'}
def load(provider):
    prefix=PROVIDERS[provider];url=os.environ.get(prefix+'_FEED_URL');token=os.environ.get(prefix+'_API_KEY')
    if not url:return {'status':'not_configured','records':[]}
    if not url.startswith('https://'):raise ValueError('A documented HTTPS licensed feed is required')
    data=request_json(url,headers={'Authorization':'Bearer '+token} if token else {})
    if not data.get('asOf') or not isinstance(data.get('records'),list):raise ProviderError('normalized_feed_contract')
    return {'status':'ok','asOf':data['asOf'],'records':data['records'],'scope':'User-configured licensed normalized feed; mapping required before model use.'}
