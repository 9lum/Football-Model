"""Auditable probability, simulation, scoring and settlement utilities."""
import math
import numpy as np
MIN_WIN_PROBABILITY=.70

def american_decimal(price):
    if not math.isfinite(price) or abs(price)<100:raise ValueError('Invalid American odds')
    return 1+price/100 if price>0 else 1+100/-price

def summarize(values,line,side,price):
    a=np.asarray(values,dtype=float)
    if len(a)<32 or not np.isfinite(a).all():raise ValueError('At least 32 finite outcome samples required')
    win=float(np.mean(a>line if side=='Over' else a<line));push=float(np.mean(a==line));decimal=american_decimal(price)
    return {'mean':float(a.mean()),'p10':float(np.quantile(a,.1)),'p50':float(np.quantile(a,.5)),'p90':float(np.quantile(a,.9)),'winProbability':win,'pushProbability':push,'fairAmerican':round(-100*win/(1-push-win)) if win/(1-push)>=.5 and 0<win<1-push else round(100*(1-push-win)/win) if win>0 else None,'expectedReturn':win*(decimal-1)-(1-win-push),'meetsProbabilityThreshold':win>=MIN_WIN_PROBABILITY,'probabilityStatus':'Empirical model estimate; market-specific calibration and all research gates still apply.'}

def simulate(values,line,side,price,draws=10000,scale=1.,seed=71):
    if not 10000<=draws<=100000:raise ValueError('Draws must be 10000–100000')
    if side not in ['Over','Under'] or not .25<=scale<=1.75:raise ValueError('Invalid scenario')
    rng=np.random.default_rng(seed);original=np.asarray(values,dtype=float)
    sampled=np.round(rng.choice(original,size=draws,replace=True)*scale)
    return {**summarize(sampled,line,side,price),'draws':draws,'scale':scale,'sourceSamples':len(original),'scenarioValidated':scale==1,'method':'Bootstrap from the learned empirical forecast. More resamples do not create more independent evidence or improve model accuracy.','histogram':np.histogram(sampled,bins=min(40,max(8,len(np.unique(sampled)))))[0].tolist(),'binEdges':np.histogram(sampled,bins=min(40,max(8,len(np.unique(sampled)))))[1].tolist()}

def settle(actual,line,side,price,participated=True):
    if actual is None:return {'status':'pending','returnPerUnit':None}
    if not participated:return {'status':'void','returnPerUnit':0.}
    if actual==line:return {'status':'push','returnPerUnit':0.}
    win=actual>line if side=='Over' else actual<line
    return {'status':'win' if win else 'loss','returnPerUnit':american_decimal(price)-1 if win else -1.}

def closing_line_value(entry_price,closing_price,entry_line,closing_line):
    if entry_line!=closing_line:return None
    return 1/american_decimal(closing_price)-1/american_decimal(entry_price)
