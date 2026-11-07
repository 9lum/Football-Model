'use client';
import {sportsbookConsensus} from '../../../web/sportsbook-consensus.mjs';
import {marketDefinitions} from '../../../web/market-core.mjs';
import SportsbookLines from './sportsbook-lines';
const fmt=(n:any)=>Number.isFinite(n)?Number(n).toLocaleString(undefined,{maximumFractionDigits:1}):'—';
export default function DashboardPropComparison({projection,quotes,market,low,high}:any){
 const prices=quotes.filter((q:any)=>q.market===market),consensus=sportsbookConsensus(prices,market);
 return <><div className="dashboard-projection-pair"><div className="dashboard-model-value"><div className="eyebrow model-label">Our model projection</div><div className="forecast-value model-favorite-value">{fmt(projection)}</div></div><div className="dashboard-consensus" title="Average posted line: one representative line per sportsbook. Uses the most balanced over/under pair, with the middle line as a fallback. This is a betting threshold, not a predicted average."><span>Sportbook AVG Proj.</span><strong>{fmt(consensus.mean)}</strong><small>{consensus.books?consensus.books+' books'+(consensus.allStale?' · stale':consensus.stale?' · some stale':''):'No posted lines'}</small></div></div><div className="small muted">{(marketDefinitions as any)[market]?.label}<br/>80% range {fmt(low)}–{fmt(high)}</div><details className="dashboard-book-dropdown"><summary><span>Sportsbook odds</span><span>{consensus.books} books <span className="prop-chevron">⌄</span></span></summary><div className="dashboard-book-content"><p className="small muted">Average uses one representative line per book. Posted lines are betting thresholds, not sportsbook forecasts.</p><SportsbookLines quotes={prices} market={market} compact minimal/></div></details></>;
}
