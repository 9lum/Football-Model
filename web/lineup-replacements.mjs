const unavailable=new Set(['OUT','INACTIVE','IR','PUP','NFI','SUSPENDED']);
/** Recognize public provider designations without upgrading them to official confirmations. */
export function effectiveInjuries(snapshot,now){
 return Object.fromEntries(Object.entries(snapshot?.injuries||{}).map(([pid,original])=>{
  const h={...original};if(h.ruledOut||h.conflict||h.scopeMismatch||!unavailable.has(String(h.status||'').toUpperCase()))return [pid,h];
  const trusted=(h.sources||[]).some(s=>{let host='';try{host=new URL(s.source).hostname}catch{return false}const provider=['espn.com','www.espn.com','site.api.espn.com','api.sleeper.app','api.sleeper.com'].includes(host),age=now-Date.parse(s.observedAt),reportedAge=now-Date.parse(s.reportedAt);return provider&&String(s.gameStatus||'').toUpperCase()===h.status&&Number(s.season)===snapshot.season&&Number(s.week)===snapshot.week&&age>=0&&age<=7200000&&(s.scopeVerified||reportedAge>=0&&reportedAge<=7*86400000)});
  return [pid,trusted?{...h,ruledOut:true,selectionTrusted:true,confirmationLevel:h.confirmed?'official':'provider',reviewRequired:true}:h];
 }));
}
export function effectiveRoster(roster,injuries){
 const groups=new Map();for(const row of roster||[]){const key=[row.team,row.position,row.slot??0].join('|');if(!groups.has(key))groups.set(key,[]);groups.get(key).push({...row});}
 return [...groups.values()].flatMap(rows=>{
  rows.sort((a,b)=>(a.rank??99)-(b.rank??99));const first=rows[0],active=rows.filter(r=>!injuries[r.playerId]?.ruledOut&&injuries[r.playerId]?.status!=='DOUBTFUL'),chosen=first?.fresh?active[0]?.playerId:null;
  return rows.map(r=>{const expected=!!chosen&&r.playerId===chosen,replacement=expected&&r.playerId!==first.playerId,conditional=replacement&&injuries[first.playerId]?.status==='DOUBTFUL',out=injuries[r.playerId]?.ruledOut;return {...r,health:injuries[r.playerId]||r.health,expectedStarter:chosen?expected:false,replacement,conditionalStarter:conditional,roleLabel:out?'Out; projection suppressed':conditional?'Conditional starter; first string doubtful':replacement?'Expected starter; first string unavailable':r.roleLabel|| (r.listedStarter?'Listed starter':'Backup')}});
 });
}
export function replacementForecasts(base,health,now){
 return (health.replacementForecasts||[]).filter(f=>Date.parse(f.kickoff)>now&&Number(f.gameId?.split('_')[1])===health.week&&!health.injuries?.[f.playerId]?.ruledOut&&health.currentTeams?.[f.playerId]!==null&&(!health.currentTeams?.[f.playerId]||health.currentTeams[f.playerId]===f.team)&&base.forecasts.some(g=>g.gameId===f.gameId&&g.team===f.team));
}
