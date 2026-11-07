import {compactOddsGroups} from './view-model.mjs';
import {marketDefinitions,marketValues} from './market-core.mjs';
export function propProjectionGroups(forecasts,quotes,{market='',requireQuotes=false}={}){
 const groups=compactOddsGroups(quotes),index=new Map(groups.map(g=>[g.first.playerId+'|'+g.first.gameId,g]));
 for(const f of forecasts){if(f.unavailable)continue;const key=f.playerId+'|'+f.gameId;let group=index.get(key);
  for(const k of Object.keys(marketDefinitions)){if(market&&k!==market)continue;const values=marketValues(f,k);if(!values?.length||!values.every(Number.isFinite))continue;if(group?.markets.some(m=>m.key===k)||requireQuotes)continue;
   const row={player:f.name,playerId:f.playerId,position:f.position,team:f.team,opponent:f.opponent,gameId:f.gameId,kickoff:f.kickoff,market:k,modelMean:values.reduce((a,b)=>a+b,0)/values.length};
   if(!group){group={first:row,markets:[]};index.set(key,group);groups.push(group)}group.markets.push({key:k,first:row,books:[]});
  }
 }
 for(const group of groups){const f=forecasts.find(f=>f.playerId===group.first.playerId&&f.gameId===group.first.gameId);if(f)group.markets=group.markets.map(m=>({...m,first:{...m.first,workloadContext:f.workloadContext,matchupFeatures:f.features||{}}}));}
 return groups;
}
