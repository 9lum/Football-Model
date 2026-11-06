"""Separate first/last touchdown scorer classifiers with pregame-only features.

Actual first/last scores include defensive/return scores when identifying the
winning scorer. Unmodeled scorers and no-TD games retain probability mass.
"""
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,log_loss
from .touchdowns import FEATURES,fit_model,american
TARGETS={'player_1st_td':'actualFirstTD','player_last_td':'actualLastTD'}
ORDER_FEATURES=FEATURES+['firstTD_last6','lastTD_last6']
def attach_labels(frame,plays):
 d=frame.copy();valid=plays.touchdown.eq(1)
 if 'play_type' in plays:valid&=plays.play_type.ne('no_play')
 if 'no_play' in plays:valid&=~plays.no_play.eq(1)
 scoring=plays[valid].sort_values(['game_id','play_id']).drop_duplicates(['game_id','play_id']);first=scoring.groupby('game_id').head(1).set_index('game_id').td_player_id;last=scoring.groupby('game_id').tail(1).set_index('game_id').td_player_id
 for target,ids in [('actualFirstTD',first),('actualLastTD',last)]:d[target]=d.player_id.eq(d.game_id.map(ids)).astype(float);d.loc[d.forecast,target]=np.nan
 d=d.sort_values(['kickoff','player_id'])
 for target,key in [('actualFirstTD','firstTD_last6'),('actualLastTD','lastTD_last6')]:d[key]=d.groupby('player_id')[target].transform(lambda s:s.shift(1).rolling(6,min_periods=1).mean())
 return d

def fit_order(d,target):return make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),LogisticRegression(C=.25,max_iter=700)).fit(d[ORDER_FEATURES],d[target])
def residual_budget(d,target):
 outcomes=d.groupby('game_id')[target].max();return float(outcomes.mean()) if len(outcomes) else 0.
def coherent(probabilities,anytime,game_ids,budget):
 p=np.minimum(np.clip(np.asarray(probabilities,float),0,1),np.clip(np.asarray(anytime,float),0,1));ids=np.asarray(game_ids)
 for game in np.unique(ids):
  mask=ids==game;total=p[mask].sum()
  if total>budget and total>0:p[mask]*=budget/total
 return p

def evaluate_and_predict(frame,plays,season):
 d=attach_labels(frame,plays);eligible=d[(~d.forecast)&d.priorGames.ge(3)&(d.carries_last4+d.targets_last4).ge(1)];future=d[d.forecast&d.priorGames.ge(3)&(d.carries_last4+d.targets_last4).ge(1)];results={};predictions={}
 for market,target in TARGETS.items():
  records=[];folds=[]
  for week in sorted(eligible[eligible.season.eq(season)].week.unique()):
   train=eligible[(eligible.season<season)|((eligible.season==season)&eligible.week.lt(week))];test=eligible[eligible.season.eq(season)&eligible.week.eq(week)]
   if len(train)<500 or len(test)<10:continue
   model=fit_order(train,target);anytime=fit_model(train).predict_proba(test[FEATURES])[:,1];budget=residual_budget(train,target);p=coherent(model.predict_proba(test[ORDER_FEATURES])[:,1],anytime,test.game_id,budget);rates=train.groupby('position')[target].mean();base=coherent(test.position.map(rates).fillna(train[target].mean()),np.ones(len(test)),test.game_id,budget);y=test[target].to_numpy();folds.append({'week':int(week),'n':len(test),'brier':brier_score_loss(y,p),'baselineBrier':brier_score_loss(y,base)});records.extend(zip(y,p,base))
  if not records:raise ValueError('Insufficient scorer-order holdout data')
  y,p,base=np.asarray(records).T;bins=[]
  for low,high in [(0,.025),(.025,.05),(.05,.1),(.1,.2),(.2,.4),(.4,1.01)]:
   mask=(p>=low)&(p<high)
   if mask.any():bins.append({'n':int(mask.sum()),'estimated':float(p[mask].mean()),'observed':float(y[mask].mean())})
  score=brier_score_loss(y,p);baseline=brier_score_loss(y,base);gap=max([abs(b['estimated']-b['observed']) for b in bins if b['n']>=50] or [1.]);results[market]={'n':len(y),'brier':score,'baselineBrier':baseline,'logLoss':log_loss(y,p,labels=[0,1]),'calibration':bins,'calibrationGap':gap,'validationPassed':bool(len(y)>=500 and score<baseline and gap<=.12),'folds':folds,'scope':'Separate first/last scorer labels, whole-week current-season holdouts. Probabilities capped by ATTD probability and a training-derived game-level mass budget; unmodeled/no-TD outcomes retain residual mass. No historical odds ROI test.'}
  fitted=fit_order(eligible,target);anytime=fit_model(eligible).predict_proba(future[FEATURES])[:,1] if len(future) else np.array([]);p=coherent(fitted.predict_proba(future[ORDER_FEATURES])[:,1],anytime,future.game_id,residual_budget(eligible,target)) if len(future) else np.array([])
  for r,value in zip(future.itertuples(),p):predictions.setdefault(r.player_id,{'gameId':r.game_id,'kickoff':r.kickoff.isoformat(),'team':r.team,'opponent':r.opponent_team,'markets':{}})['markets'][market]={'probability':float(value),'fairOdds':american(value),'validationPassed':results[market]['validationPassed'],'status':'model estimate' if results[market]['validationPassed'] else 'research estimate'}
 return results,predictions
