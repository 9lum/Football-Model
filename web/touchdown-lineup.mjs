/** Current lineup gates are applied to every future TD surface; old forecasts remain intact. */
export function applyTouchdownLineup(report,bundle,now=Date.now()){
 if(!report)return report;const health=bundle?.healthSnapshot,age=now-Date.parse(health?.generatedAt);if(!(age>=0&&age<=7200000))return report;
 const decisions=new Map(Object.entries(health.lineupPolicy?.modelGeneratedAt===bundle.generatedAt?health.lineupPolicy?.players||{}:{}));
 for(const f of bundle.forecasts||[]){if(Date.parse(f.kickoff)<=now||Number(f.gameId?.split('_')[1])!==health.week)continue;if(f.unavailable||f.health?.ruledOut)decisions.set(f.playerId,{gameId:f.gameId,team:f.team,reason:f.forecastEligibility?.reason||'Current availability or roster excludes this player from upcoming projections.'})}
 for(const p of bundle.players||[]){if(!p.health?.scopeMismatch&&p.health?.ruledOut){const e=report.allPlayerOdds?.[p.playerId];if(e&&Number(e.gameId?.split('_')[1])===health.week)decisions.set(p.playerId,{gameId:e.gameId,team:e.team,reason:'Current availability report rules this player out.'})}}
 const blocked=(pid,gid)=>decisions.get(pid)?.gameId===gid;
 const odds=Object.fromEntries(Object.entries(report.allPlayerOdds||{}).map(([pid,e])=>[pid,Date.parse(e.kickoff)>now&&blocked(pid,e.gameId)?{...e,status:'unavailable',markets:{},reason:decisions.get(pid).reason,lineupPolicy:decisions.get(pid)}:e]));
 const games=(report.games||[]).map(g=>Date.parse(g.kickoff)>now?{...g,players:(g.players||[]).filter(p=>!blocked(p.playerId,g.gameId)),candidates:(g.candidates||[]).filter(p=>!blocked(p.playerId,g.gameId))}:g);
 return {...report,allPlayerOdds:odds,games,lineupPolicyAppliedAt:health.generatedAt};
}
