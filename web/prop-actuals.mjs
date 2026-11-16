import {marketDefinitions} from './market-core.mjs';
// Exact player + game identity prevents a previous week's box score leaking into a new prop.
export function propActualIndex(snapshot){
 const index=new Map();
 for(const row of snapshot?.rows||[]){
  if(!row.playerId||!row.gameId)continue;
  const key=row.playerId+'|'+row.gameId,old=index.get(key);
  if(!old||(Date.parse(row.observedAt)||0)>=(Date.parse(old.observedAt)||0))index.set(key,row);
 }
 return index;
}
export function propActual(row,market){
 const target=marketDefinitions[market]?.target,value=row?.basic?.[target];
 return Number.isFinite(value)?{value,completed:row.completed===true,observedAt:row.observedAt,source:row.source}:null;
}
