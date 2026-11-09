/** Use verified published pregame evidence, never today's injuries on a finished game. */
export function archivedMatchup(archive,gameId){
 if(!archive||archive.gameId!==gameId||archive.kind!=='published_pregame'||!archive.sourceCommit||!(Date.parse(archive.issuedAt)<Date.parse(archive.kickoff)))return null;
 if(!(archive.bundle?.forecasts||[]).length||archive.bundle.forecasts.some(f=>f.gameId!==gameId||!(Date.parse(archive.issuedAt)<Date.parse(f.kickoff))))return null;
 return archive;
}
export function mergeMatchupBundle(current,archived,gameId){
 if(!archived)return current;
 const ids=new Set(archived.forecasts.map(f=>f.playerId));
 return {...current,healthSnapshot:archived.healthSnapshot,healthState:archived.healthState,players:[...(current?.players||[]).filter(p=>!ids.has(p.playerId)),...(archived.players||[]).map(p=>{const live=current?.players?.find(v=>v.playerId===p.playerId),history=new Map([...(p.history||[]),...(live?.history||[])].map(g=>[g.gameId||`${g.season}-${g.week}`,g]));return {...p,history:[...history.values()].sort((a,b)=>(a.season-b.season)||(a.week-b.week))}})],forecasts:[...(current?.forecasts||[]).filter(f=>f.gameId!==gameId),...archived.forecasts]};
}
