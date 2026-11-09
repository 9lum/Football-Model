import {matchGameMarket} from './game-markets.mjs';
/** Rebuild only actual archived quotes, preserving provider and observation timestamps. */
export function retainedGameOdds(events=[],archive={},games=[],names={}){
 const result=[...events];
 for(const g of games){
  const current=matchGameMarket(result,g,names);
  if(current?.bookmakers?.some(b=>b.markets?.some(m=>m.outcomes?.some(q=>Number.isFinite(q.price)))))continue;
  if(current)result.splice(result.indexOf(current),1);
  const normalize=t=>t==='LA'?'LAR':t==='WSH'?'WAS':t==='JAC'?'JAX':t;
  const home=names[normalize(g.home_team)]||g.home_team,away=names[normalize(g.away_team)]||g.away_team;
  const rows=(archive.observations||[]).filter(r=>r.homeTeam===home&&r.awayTeam===away&&Math.abs(Date.parse(r.kickoff)-Date.parse(g.kickoff))<3600000&&['h2h','spreads','totals'].includes(r.market));
  const books=new Map();
  for(const r of rows.sort((a,b)=>Date.parse(a.observedAt)-Date.parse(b.observedAt))){
   const key=r.source+'|'+r.bookKey;if(!books.has(key))books.set(key,{key,title:r.book,source:r.source,markets:new Map(),observed_at:r.observedAt,archived:true});
   const b=books.get(key);if(!b.markets.has(r.market))b.markets.set(r.market,new Map());b.markets.get(r.market).set(r.side,r);b.observed_at=r.observedAt;
  }
  if(!books.size)continue;
  result.push({id:'archive-'+g.game_id,home_team:home,away_team:away,commence_time:g.kickoff,archived:true,bookmakers:[...books.values()].map(b=>({...b,markets:[...b.markets.entries()].map(([key,sides])=>{const quotes=[...sides.values()];return {key,last_update:quotes.every(q=>q.providerUpdatedAt)?quotes.map(q=>q.providerUpdatedAt).sort()[0]:null,observed_at:quotes.map(q=>q.observedAt).sort()[0],outcomes:quotes.map(q=>({name:q.side,price:q.price,...(q.market==='h2h'?{}:{point:q.point})}))}})}))});
 }
 return result;
}
