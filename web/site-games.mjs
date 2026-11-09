import {teamNames} from './market-core.mjs';
const code=t=>t==='LA'?'LAR':t==='WSH'?'WAS':t==='JAC'?'JAX':Object.keys(teamNames).find(k=>teamNames[k]===t)||t;
/** Keep archived fixtures selectable when the upcoming-only feed rolls forward. */
export function siteGames(schedule=[],history={},touchdowns={},snapshot={}){
 const games=new Map();
 for(const g of [...(history.projections||[]),...(touchdowns.games||[])])if(g.gameId&&g.kickoff)games.set(g.gameId,{game_id:g.gameId,home_team:code(g.homeTeam),away_team:code(g.awayTeam),kickoff:g.kickoff,season:Number(g.gameId.split('_')[0]),week:Number(g.gameId.split('_')[1])});
 for(const g of schedule)games.set(g.game_id,g);
 for(const r of snapshot.results||[]){
  if(!r.completed)continue;
  const home=code(r.homeTeam),away=code(r.awayTeam);
  const matches=[...games.values()].filter(g=>code(g.home_team)===home&&code(g.away_team)===away&&Math.abs(Date.parse(g.kickoff)-Date.parse(r.kickoff))<=6*3600000);
  if(matches.length===1){const g=matches[0];games.set(g.game_id,{...g,home_score:r.homeScore,away_score:r.awayScore,completed:true,espn:r.id?.replace('espn-','')});}
  else if(!matches.length)games.set(r.id,{game_id:r.id,home_team:home,away_team:away,kickoff:r.kickoff,home_score:r.homeScore,away_score:r.awayScore,completed:true,espn:r.id?.replace('espn-','')});
 }
 return [...games.values()].sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff));
}
