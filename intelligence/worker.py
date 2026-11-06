import datetime as dt
import json
import os
import time
from .ingest import run
from .database import sync
from scripts.refresh_odds import collect
while True:
    for name,fn in [('providers',run),('odds',collect),('database',sync)]:
        try:
            result=fn();print(json.dumps({'job':name,'finishedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'status':result.get('status','ok')}),flush=True)
        except Exception as error:print(json.dumps({'job':name,'status':'failed','error':type(error).__name__}),flush=True)
    time.sleep(max(900,int(os.environ.get('WORKER_INTERVAL_SECONDS','21600'))))
