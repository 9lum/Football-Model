import {archivedMatchup} from './matchup-archive.mjs';
import {applyAvailability} from './availability.mjs';
import {marketDefinitions,scanMarkets,teamNames} from './market-core.mjs';
import {availablePlayerMarkets} from './player-game-data.mjs';
import {propProjectionGroups} from './prop-projections.mjs';
import {propActualIndex} from './prop-actuals.mjs';

/** Compact genuine pregame evidence. Never recompute a past forecast from today's model. */
const compactRow=r=>Object.fromEntries(['player','playerId','position','team','opponent','gameId','kickoff','market','modelMean','book','side','line','price','probability','push','ev','priceTimestamp','flags','candidate'].filter(k=>r[k]!==undefined).map(k=>[k,r[k]]));
export function buildPropResults(archives=[],actuals={}){
 const actualIndex=propActualIndex(actuals),groups=new Map();
 for(const input of archives){
  const a=archivedMatchup(input,input?.gameId);if(!a)continue;
  const b=applyAvailability(a.bundle,a.availability,Date.parse(a.issuedAt),new Set(),{historical:true});
  const quotes=scanMarkets(b,a.oddsEvents||[],Date.parse(a.issuedAt)).map(q=>({...q,candidate:false}));
  for(const group of propProjectionGroups(b.forecasts,quotes)){
   const p=group.first,key=p.playerId+'|'+p.gameId;
   group.first={...compactRow(p),historical:true,issuedAt:a.issuedAt,sourceCommit:a.sourceCommit};
   group.markets=group.markets.map(m=>({...m,books:m.books.map(b=>Object.fromEntries(Object.entries(b).map(([side,q])=>[side,compactRow(q)]))),first:{...compactRow(m.first),historical:true,issuedAt:a.issuedAt,sourceCommit:a.sourceCommit}}));
   groups.set(key,group);
  }
 }
 // Actual participants remain visible even without a saved forecast; missing predictions stay blank.
 for(const [key,r] of actualIndex){
  if(!r.completed)continue;
  let group=groups.get(key);const player={player:r.name,playerId:r.playerId,position:r.position,team:r.team,opponent:r.opponent,gameId:r.gameId,kickoff:r.kickoff,historical:true};
  if(!group){group={first:player,markets:[]};groups.set(key,group)}
  for(const market of availablePlayerMarkets({position:r.position},null,[r]))if(!group.markets.some(m=>m.key===market))group.markets.push({key:market,first:{...player,market,modelMean:null},books:[]});
 }
 for(const [key,g] of groups){const r=actualIndex.get(key);g.actualRow=r||null;g.first.completed=!!r?.completed;g.markets=g.markets.map(m=>({...m,first:{modelMean:m.first.modelMean,sourceCommit:m.first.sourceCommit}}));}
 return {schemaVersion:1,groups:[...groups.values()],scope:'Saved pregame projections and collected book quotes, joined by exact player and game to verified actuals. Missing forecasts, prices and actuals are never replaced with zero. Past games are not repriced.'};
}
export function currentWeekPropResults(feed,{season,week,games=[],market='',team='',position='',search='',book='',only70=false}={}){
 const finals=new Set(games.filter(g=>g.completed===true).map(g=>g.game_id));
 return (feed?.groups||[]).filter(g=>{const p=g.first,parts=String(p.gameId).split('_');return Number(parts[0])===Number(season)&&Number(parts[1])===Number(week)&&(p.completed||finals.has(p.gameId))&&(!team||p.team===team)&&(!position||p.position===position)&&[p.player,p.team,teamNames[p.team]].join(' ').toLowerCase().includes(search.toLowerCase())}).map(g=>({...g,markets:g.markets.filter(m=>!market||m.key===market).map(m=>({...m,books:m.books.map(b=>Object.fromEntries(Object.entries(b).filter(([,q])=>q&&(!book||q.book===book)&&(!only70||q.probability>=.7)))).filter(b=>Object.keys(b).length)})).filter(m=>!(book||only70)||m.books.length)})).filter(g=>g.markets.length);
}
