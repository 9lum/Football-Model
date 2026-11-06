export function touchdownModelOdds(player,report){
 const entry=report?.allPlayerOdds?.[player?.playerId],empty={markets:{},reason:'No current eligible model forecast'};
 if(!entry)return empty;if(entry.status==='unavailable')return entry;
 if(player?.gameId&&entry.gameId!==player.gameId)return empty;
 const time=Date.parse(player?.kickoff),modelTime=Date.parse(entry.kickoff);
 if(!Number.isFinite(time)||!Number.isFinite(modelTime)||Math.abs(time-modelTime)>=3600000)return empty;
 if(player?.team&&entry.team!==player.team)return empty;
 return entry;
}
