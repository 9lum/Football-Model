import {touchdownGameState} from './touchdown-game-state.mjs';
const team=t=>t==='LA'?'LAR':t==='WSH'?'WAS':t==='JAC'?'JAX':t;
export function matchupResult(game,snapshot,history){
 if(!game)return null;
 const match={homeTeam:game.home_team,awayTeam:game.away_team,kickoff:game.kickoff,status:'upcoming'};
 const state=touchdownGameState(match,snapshot);
 if(state.status!=='finished')return null;
 const p=history?.projections?.find(p=>p.gameId===game.game_id&&team(p.homeTeam)===team(game.home_team)&&team(p.awayTeam)===team(game.away_team)&&Date.parse(p.kickoff)===Date.parse(game.kickoff)&&Date.parse(p.projectedAt)<Date.parse(game.kickoff));
 if(!p)return {state,projection:null,checks:[]};
 const pick=p.probHomeWin>p.probAwayWin?p.homeTeam:p.probAwayWin>p.probHomeWin?p.awayTeam:null;
 const actualTotal=state.homeScore+state.awayScore,actualMargin=state.homeScore-state.awayScore;
 const checks=[{label:'Winner pick',detail:pick||'No lean',tone:!pick||!state.winner?'neutral':team(pick)===team(state.winner)?'good':'bad',result:!pick||!state.winner?'No grade':team(pick)===team(state.winner)?'Correct':'Missed'}];
 for(const [label,range,actual] of [['Total · 80% range',p.totalInterval80,actualTotal],['Home margin · 80% range',p.marginInterval80,actualMargin]]){
  if(Array.isArray(range)&&range.length===2&&range.every(Number.isFinite))checks.push({label,detail:`${range[0].toFixed(1)}–${range[1].toFixed(1)} · actual ${actual}`,tone:actual>=range[0]&&actual<=range[1]?'good':'bad',result:actual>=range[0]&&actual<=range[1]?'Inside range':'Outside range'});
 }
 return {state,projection:p,checks};
}
