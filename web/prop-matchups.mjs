export function groupPropMatchups(players){
 const groups=new Map();
 for(const player of players){const p=player.first,teams=[p.team,p.opponent].filter(Boolean).sort(),key=p.gameId||JSON.stringify([teams,p.kickoff]);if(!groups.has(key))groups.set(key,{key,gameId:p.gameId,kickoff:p.kickoff,teams,players:[]});groups.get(key).players.push(player)}
 return [...groups.values()].map(g=>({...g,players:g.players.sort((a,b)=>String(a.first.team).localeCompare(String(b.first.team))||String(a.first.player).localeCompare(String(b.first.player)))})).sort((a,b)=>{const time=x=>Number.isFinite(Date.parse(x))?Date.parse(x):Infinity;return time(a.kickoff)-time(b.kickoff)||String(a.key).localeCompare(String(b.key))});
}
