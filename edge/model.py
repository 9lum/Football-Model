"""Distributional forest + chronological evaluation, with no fabricated odds ROI."""
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer

from .config import THRESHOLDS
TARGETS=['receiving_yards','receptions']
class DistributionForest:
    def __init__(self,trees=96,min_leaf=25,seed=71):
        self.imputer=SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)
        self.forest=RandomForestRegressor(n_estimators=trees,min_samples_leaf=min_leaf,max_depth=12,max_features=.8,n_jobs=2,random_state=seed)
        self.seed=seed
    def fit(self,x,y):
        x=self.imputer.fit_transform(x.replace([np.inf,-np.inf],np.nan))
        self.y=np.asarray(y,dtype=float)
        self.target_count=self.y.shape[1]
        scale=np.std(self.y,axis=0)
        self.forest.fit(x,self.y/np.where(scale>0,scale,1))
        leaves=self.forest.apply(x)
        self.pools=[]
        for i in range(leaves.shape[1]):
            order=np.argsort(leaves[:,i],kind='stable')
            keys,starts=np.unique(leaves[order,i],return_index=True)
            groups=np.split(order,starts[1:])
            self.pools.append(dict(zip(keys,groups)))
        return self
    def predict_mean(self,x):
        x=self.imputer.transform(x.replace([np.inf,-np.inf],np.nan))
        leaves=self.forest.apply(x);result=np.zeros((len(x),self.target_count))
        for tree,pools in enumerate(self.pools):
            means={key:self.y[indices].mean(axis=0) for key,indices in pools.items()}
            result+=np.asarray([means[leaf] for leaf in leaves[:,tree]])
        return result/len(self.pools)
    def sample(self,x,draws=512):
        x=self.imputer.transform(x.replace([np.inf,-np.inf],np.nan))
        leaves=self.forest.apply(x)
        rng=np.random.default_rng(self.seed)
        result=np.empty((len(x),draws,self.target_count))
        # Each tree leaf supplies observed joint yards/receptions, preserving their dependence.
        for row in range(len(x)):
            for j,tree in enumerate(rng.integers(0,len(self.pools),size=draws)):
                index=rng.choice(self.pools[tree][leaves[row,tree]])
                result[row,j]=self.y[index]
        return result

def crps(draws,actual):
    """Exact empirical CRPS, averaged over rows. Lower is better."""
    a=np.sort(draws,axis=1);n=a.shape[1]
    return np.mean(np.mean(np.abs(a-actual[:,None]),axis=1)-np.sum(a*(2*np.arange(1,n+1)-n-1),axis=1)/(n*n))

def scores(samples,y,baseline,targets=None):
    targets=targets or TARGETS
    result={}
    for i,key in enumerate(targets):
        a=samples[:,:,i];actual=np.asarray(y[key]);mean=a.mean(axis=1)
        low,high=np.quantile(a,[.1,.9],axis=1)
        thresholds=THRESHOLDS[key]
        reliability=[];briers=[];log_losses=[];high_prob=[];high_actual=[]
        for line in thresholds:
            p=(a>line).mean(axis=1);outcome=(actual>line).astype(float)
            briers.extend((p-outcome)**2)
            for estimated,observed in [(p,outcome),(1-p,1-outcome)]:
                chosen=estimated>=.70
                high_prob.extend(estimated[chosen]);high_actual.extend(observed[chosen])
            clipped=np.clip(p,1e-6,1-1e-6);log_losses.extend(-(outcome*np.log(clipped)+(1-outcome)*np.log(1-clipped)))
            for lower in np.arange(0,1,.1):
                select=(p>=lower)&(p<lower+.1 if lower<.9 else p<=1)
                if select.any():
                    reliability.append({'line':line,'bin':round(float(lower),1),'n':int(select.sum()),'predicted':float(p[select].mean()),'observed':float(outcome[select].mean())})
        result[key]={'n':len(actual),'mae':float(np.mean(np.abs(mean-actual))),'rmse':float(np.sqrt(np.mean((mean-actual)**2))),
                     'rollingBaselineMae':float(np.mean(np.abs(np.asarray(baseline[key])-actual))),
                     'crps':float(crps(a,actual)), 'coverage80':float(((actual>=low)&(actual<=high)).mean()),
                     'meanWidth80':float((high-low).mean()),'fixedThresholdBrier':float(np.mean(briers)),'fixedThresholdLogLoss':float(np.mean(log_losses)),
                     'probability70Cohort':{'n':len(high_actual),'meanEstimated':float(np.mean(high_prob)) if high_prob else None,'observedWinRate':float(np.mean(high_actual)) if high_actual else None,'scope':'Pooled fixed thresholds, both sides; not actual historical sportsbook wagers.'},'reliability':reliability}
    return result

def walk_forward(frame,features,season,trees=96,min_train=500,complete_weeks=None,targets=None,positions=None):
    targets=targets or TARGETS
    """Expanding training window, held out by complete NFL week."""
    eligible=frame[(~frame.forecast)&(frame.prior_games>=3)].dropna(subset=targets)
    if positions is not None: eligible=eligible[eligible.position.isin(positions)]
    weeks=sorted(eligible.loc[eligible.season.eq(season),'week'].unique())
    if not weeks:
        raise ValueError('No completed current-season weeks available')
    all_samples=[];all_y=[];all_base=[];folds=[];details=[]
    for week in weeks:
        # Every game in the tested week is excluded, including Thursday's game.
        train=eligible[(eligible.season<season)|((eligible.season==season)&(eligible.week<week))]
        test=eligible[(eligible.season==season)&(eligible.week==week)]
        if len(train)<min_train or len(test)==0:
            continue
        fitted=DistributionForest(trees=trees).fit(train[features],train[targets])
        samples=fitted.sample(test[features])
        base={key:test[key+'_last6'].fillna(train[key].median()).to_numpy() for key in targets}
        metric=scores(samples,test[targets],base,targets)
        folds.append({'week':int(week),'trainRows':len(train),'testRows':len(test),'metrics':metric})
        all_samples.append(samples);all_y.append(test[targets]);all_base.append(base)
        details.extend({'game_id':row.game_id,'player_id':row.player_id,'week':int(week),'team':row.team,'opponent':row.opponent_team,'position':row.position,'kickoff':row.kickoff.isoformat(),
                        **{key:{'actual':float(getattr(row,key)),'mean':float(samples[j,:,i].mean()),'baseline':float(base[key][j]),'p10':float(np.quantile(samples[j,:,i],.1)),'p90':float(np.quantile(samples[j,:,i],.9))} for i,key in enumerate(targets)}}
                       for j,row in enumerate(test.itertuples()))
    if not folds:
        raise ValueError('Insufficient historical games for chronological evaluation')
    import pandas as pd
    y=pd.concat(all_y,ignore_index=True)
    baseline={key:np.concatenate([v[key] for v in all_base]) for key in targets}
    aggregate=scores(np.concatenate(all_samples),y,baseline,targets)
    # Latest week is reported separately and never used for configuration selection.
    complete_folds=[f for f in folds if complete_weeks is None or f['week'] in complete_weeks]
    if not complete_folds:
        raise ValueError('No fully completed season week is available for the final holdout')
    return {'season':season,'evaluation':'Reconstructed historical features; final-corrected public outcomes. Not a point-in-time odds backtest.',
            'aggregate':aggregate,'folds':folds,'latestWeekHoldout':complete_folds[-1],
            'latestObservedWeek':folds[-1]['week'],
            'partialWeeks':[f['week'] for f in folds if complete_weeks is not None and f['week'] not in complete_weeks],
            'configurationTunedOnLatestWeek':False,'roi':None,'closingLineValue':None,
            'predictions':details}
