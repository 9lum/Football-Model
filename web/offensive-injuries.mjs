import {groupResearchRoster} from './research-roster.mjs';
export function offensiveInjuries(players,teams,snapshot,gameId,now=Date.now()){
 const parts=String(gameId||'').split('_'),age=now-Date.parse(snapshot?.generatedAt),available=!!snapshot&&snapshot.season===Number(parts[0])&&snapshot.week===Number(parts[1])&&age>=0&&age<=7200000;
 if(!available)return {available:false,groups:[],count:0};
 const flagged=(players||[]).filter(p=>{if(!teams.includes(p.team)||!['QB','RB','HB','WR','TE'].includes(p.position)||!p.health||p.health.scopeMismatch)return false;const h=p.health,status=String(h.status||'').toUpperCase();if(h.ruledOut||['QUESTIONABLE','DOUBTFUL','OUT','IR','PUP','NFI','INACTIVE','SUSPENDED'].includes(status))return true;if(['ACTIVE','HEALTHY','AVAILABLE','CLEARED','NOT_LISTED'].includes(status))return false;return typeof h.injury==='string'&&!!h.injury.trim()&&!/^(unknown|none|not injury related|rest)$/i.test(String(h.injury).trim())});
 const groups=groupResearchRoster(flagged,players).sort((a,b)=>teams.indexOf(a.team)-teams.indexOf(b.team));
 return {available:true,groups,count:flagged.length};
}
