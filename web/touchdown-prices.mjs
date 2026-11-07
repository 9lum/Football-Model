import {teamNames} from './market-core.mjs';
const clean=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
export const touchdownMarkets=[['player_anytime_td','Anytime TD'],['player_1st_td','First TD'],['player_last_td','Last TD'],['player_tds_over','2+ TDs']];
export function touchdownPrices(player,snapshot,now=Date.now()){
 const result=Object.fromEntries(touchdownMarkets.map(([key])=>[key,[]])),name=clean(player?.name||player?.player),kickoff=Date.parse(player?.kickoff),clubs=[teamNames[player?.team],teamNames[player?.opponent]].filter(Boolean);
 if(!name||!Number.isFinite(kickoff)||clubs.length!==2)return result;
 for(const event of snapshot?.data||[]){if(!clubs.includes(event.home_team)||!clubs.includes(event.away_team)||Math.abs(Date.parse(event.commence_time)-kickoff)>=3600000)continue;
  for(const book of event.bookmakers||[])for(const market of book.markets||[]){if(!result[market.key])continue;for(const o of market.outcomes||[]){if(market.key==='player_tds_over'&&o.point!==1.5)continue;const actual=o.name==='Yes'?o.description:['No','Yes','Over','Under'].includes(o.name)?null:o.name;if(clean(actual)!==name||!Number.isFinite(o.price)||Math.abs(o.price)<100)continue;const publicSnapshot=market.sourceKind==='public_web',updatedAt=publicSnapshot?null:market.last_update||book.last_update,age=now-Date.parse(updatedAt);result[market.key].push({book:book.title,price:o.price,updatedAt,publicSnapshot,observedAt:market.observedAt,source:market.source,link:o.link,fresh:!publicSnapshot&&age>=0&&age<=180000&&kickoff>now})}}
 }
 for(const key of Object.keys(result))result[key].sort((a,b)=>Number(b.fresh)-Number(a.fresh)||b.price-a.price);return result;
}
