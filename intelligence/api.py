"""FastAPI research service. Public read endpoints; optional bearer auth for local/private deployments."""
import json
import os
import secrets
from pathlib import Path
from typing import Literal
from functools import lru_cache
from fastapi import FastAPI,HTTPException,Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from .research import simulate
ROOT=Path(__file__).resolve().parents[1];DATA=Path(os.environ.get('DATA_DIRECTORY',str(ROOT/'data')))
app=FastAPI(title='Projections n Shit — Research API',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=os.environ.get('CORS_ORIGINS','http://localhost:3000').split(','),allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'])
FILES={'latest','validation','projection-results','providers','weather','balldontlie','advanced-stats','upcoming-games','odds','odds-history','availability','availability-history','oos-predictions'}
@lru_cache(maxsize=20)
def cached(path,mtime):return json.loads(Path(path).read_text())
def snapshot(name):
    if name not in FILES:raise HTTPException(404,'Unknown dataset')
    path=DATA/(name+'.json')
    if not path.exists():raise HTTPException(503,'Dataset has not been published')
    return cached(str(path),path.stat().st_mtime_ns)
@app.middleware('http')
async def auth(request:Request,call_next):
    token=os.environ.get('API_AUTH_TOKEN')
    if token and not secrets.compare_digest(request.headers.get('Authorization',''),'Bearer '+token):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Authentication required'},status_code=401)
    return await call_next(request)
@app.get('/api/health')
def health():return {'status':'ok','availableDatasets':[p.stem for p in DATA.glob('*.json') if p.stem in FILES],'minimumEstimatedWinProbability':.70,'databaseConfigured':bool(os.environ.get('DATABASE_URL'))}
@app.get('/api/snapshots/{name}')
def read_snapshot(name:str):return snapshot(name.removesuffix('.json'))
@app.get('/api/players')
def players(position:str|None=None,team:str|None=None,q:str=''):
    return [p for p in snapshot('latest').get('players',[]) if (not position or p['position']==position.upper()) and (not team or p['team']==team.upper()) and q.lower() in p['name'].lower()]
class SimulationInput(BaseModel):
    playerId:str
    market:str
    line:float=Field(ge=0,le=1000)
    side:Literal['Over','Under']='Over'
    price:int=-110
    scale:float=Field(default=1.,ge=.25,le=1.75)
    draws:int=Field(default=10000,ge=10000,le=100000)
@app.post('/api/simulate')
def simulation(body:SimulationInput):
    forecast=next((f for f in snapshot('latest')['forecasts'] if f['playerId']==body.playerId),None)
    values=forecast.get('marketSamples',{}).get(body.market,{}).get('values') if forecast else None
    if not values:raise HTTPException(404,'No model distribution for that player and market')
    try:return simulate(values,body.line,body.side,body.price,body.draws,body.scale)
    except ValueError as error:raise HTTPException(422,str(error)) from None
@app.get('/api/lake/catalog')
def catalog():
    lake=Path(os.environ.get('LAKE_DIRECTORY',str(ROOT/'work/lake')))
    return [{'dataset':p.stem,'bytes':p.stat().st_size} for p in lake.glob('*.parquet')]
