/** Merge provider aliases using verified IDs; same names alone are never an identity key. */
export function uniquePlayers(rows=[]){
 const ids=new Map(),espn=new Map(),out=[];
 const score=p=>(String(p.playerId||'').startsWith('00-')?8:0)+(p.roster?.fresh?4:0)+(p.history?.length?2:0)+(p.health?1:0);
 for(const p of rows){if(!p?.playerId)continue;const eid=String(p.espnId||p.roster?.espnId||'').replace(/\.0$/,''),alias=String(p.playerId).startsWith('espn-')?String(p.playerId).slice(5):eid,index=ids.get(p.playerId)??(alias?espn.get(alias):undefined);
 if(index===undefined){const i=out.length;out.push({...p});ids.set(p.playerId,i);if(alias)espn.set(alias,i)}else{const old=out[index],preferred=score(p)>score(old)?p:old,other=preferred===p?old:p;out[index]={...other,...preferred,espnId:preferred.espnId||other.espnId,history:preferred.history?.length?preferred.history:other.history};ids.set(p.playerId,index);if(alias)espn.set(alias,index)}}
 return out;
}
