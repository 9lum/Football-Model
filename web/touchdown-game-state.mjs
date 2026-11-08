import {teamNames} from './market-core.mjs';
const code=t=>t==='LA'?'LAR':t==='WSH'?'WAS':t==='JAC'?'JAX':Object.keys(teamNames).find(k=>teamNames[k]===t)||t;
export function touchdownGameState(game,snapshot,now=Date.now()){
 const kickoff=Date.parse(game.kickoff);
 const result=(snapshot?.results||[]).filter(r=>code(r.homeTeam)===code(game.homeTeam)&&code(r.awayTeam)===code(game.awayTeam)&&Number.isFinite(kickoff)&&Date.parse(r.kickoff)===kickoff).sort((a,b)=>Date.parse(b.observedAt)-Date.parse(a.observedAt))[0];
 const final=result?.completed===true&&[result.homeScore,result.awayScore].every(v=>typeof v==='number'&&Number.isInteger(v)&&v>=0);
 if(final)return {status:'finished',label:result.homeScore===result.awayScore?'Finished · Tie':'Finished',winner:result.homeScore===result.awayScore?null:result.homeScore>result.awayScore?game.homeTeam:game.awayTeam,homeScore:result.homeScore,awayScore:result.awayScore,observedAt:result.observedAt};
 if(result?.state==='in')return {status:'in-progress',label:'In progress',winner:null,homeScore:result.homeScore,awayScore:result.awayScore,detail:result.detail||null,observedAt:result.observedAt};
 if(result?.state==='post'||game.status!=='upcoming'||Number.isFinite(kickoff)&&now>=kickoff)return {status:'started',label:'Started · final unconfirmed',winner:null};
 return {status:'upcoming',label:'Upcoming',winner:null};
}
