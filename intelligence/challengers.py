"""Prior-season model selection, then untouched current-season evaluation. Never auto-promote."""
import datetime as dt
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor
from edge.data import normalize_stats,schedule_rows,add_snap_zeros
from edge.features import prepare
from edge.config import FAMILIES
from edge.advanced import attach
ROOT=Path(__file__).resolve().parents[1]
def run():
    lake=ROOT/'work/lake';out=ROOT/'data';stats=pd.read_parquet(lake/'player_stats.parquet');season=int(stats.season.max());schedules=schedule_rows(pd.read_parquet(lake/'schedules.parquet'));stats=normalize_stats(stats,positions=['QB','RB','WR','TE']);stats,_=add_snap_zeros(stats,pd.read_parquet(lake/'snaps.parquet'),pd.read_parquet(lake/'players.parquet'));stats,ngs=attach(stats,2021,season);frame,features=prepare(stats,schedules);rows=[]
    for family,spec in FAMILIES.items():
        cohort=frame[(~frame.forecast)&frame.position.isin(spec['positions'])&frame.prior_games.ge(3)]
        train=cohort[cohort.season.lt(season-1)];dev=cohort[cohort.season.eq(season-1)];test=cohort[cohort.season.eq(season)]
        for target in spec['targets']:
            tr=train.dropna(subset=[target]);dv=dev.dropna(subset=[target]);te=test.dropna(subset=[target]);
            if len(tr)<500 or len(dv)<100 or len(te)<50:continue
            imputer=SimpleImputer(strategy='median',keep_empty_features=True);x=imputer.fit_transform(tr[features].replace([np.inf,-np.inf],np.nan));xd=imputer.transform(dv[features].replace([np.inf,-np.inf],np.nan));xt=imputer.transform(te[features].replace([np.inf,-np.inf],np.nan))
            models={'LightGBM':LGBMRegressor(objective='quantile',alpha=.5,n_estimators=120,num_leaves=15,min_child_samples=60,learning_rate=.05,n_jobs=2,verbosity=-1,random_state=71),'XGBoost':XGBRegressor(objective='reg:absoluteerror',n_estimators=120,max_depth=3,learning_rate=.05,n_jobs=2,random_state=71)}
            for name,model in models.items():
                model.fit(x,tr[target]);pdv=np.maximum(0,model.predict(xd));pt=np.maximum(0,model.predict(xt));base=te[target+'_last6'].fillna(tr[target].median()).to_numpy();rows.append({'family':family,'target':target,'model':name,'trainingThrough':season-2,'developmentSeason':season-1,'developmentN':len(dv),'developmentMae':float(np.mean(np.abs(pdv-dv[target]))),'testSeason':season,'testN':len(te),'testMae':float(np.mean(np.abs(pt-te[target]))),'testRmse':float(np.sqrt(np.mean((pt-te[target])**2))),'baselineMae':float(np.mean(np.abs(base-te[target]))),'promoted':False})
    for target in {r['target'] for r in rows}:
        candidates=[r for r in rows if r['target']==target];winner=min(candidates,key=lambda r:r['developmentMae'])['model']
        for r in candidates:r['selectedOnPriorDevelopment']=r['model']==winner
    value={'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'selectionScope':'Hyperparameters fixed in code; select model by earlier-season development MAE, then evaluate current-season outcomes. Current-season results never select the winner.','status':'Research challengers; not promoted to distributional forecasts','probabilityScope':'Median-regression challengers have no calibrated probability distribution and cannot qualify as betting picks.','results':rows,'ngsSources':ngs}
    (out/'challengers.json').write_text(json.dumps(value,separators=(',',':')));print(json.dumps({'challengerTests':len(rows),'promoted':0}))
if __name__=='__main__':run()
