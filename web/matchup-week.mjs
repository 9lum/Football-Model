import {matchTouchdownResult} from './touchdown-game-state.mjs';
import {teamNames} from './market-core.mjs';
const code=t=>t==='LA'?'LAR':t==='WSH'?'WAS':Object.keys(teamNames).find(k=>teamNames[k]===t)||t;
const ordinal=g=>Number(g.season)*100+Number(g.week);
export function eventInGames(event,games){return games.some(g=>code(g.home_team)===code(event.home_team)&&code(g.away_team)===code(event.away_team)&&Math.abs(Date.parse(g.kickoff)-Date.parse(event.commence_time))<=21600000);}
/** Whole-week rollover: every scheduled event, including Monday/delayed games, must be confirmed final. */
export function matchupWeek(games=[],snapshot={},now=Date.now()){
 const groups=new Map();
 for(const g of games){if(!Number.isFinite(Number(g.season))||!Number.isFinite(Number(g.week)))continue;const key=ordinal(g);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(g);}
 const cover=(snapshot?.weekCoverage||[]).filter(w=>w.eventIds?.length&&snapshot.results?.some(r=>w.eventIds.includes(r.id)&&Math.abs(Date.parse(r.kickoff)-now)<21*86400000));
 const covered=cover.map(w=>({key:Number(w.season)*100+Number(w.week),...w,finished:w.eventIds.every(id=>snapshot.results?.some(r=>r.id===id&&r.completed===true))&&(groups.get(Number(w.season)*100+Number(w.week))||[]).every(g=>g.completed||matchTouchdownResult({homeTeam:g.home_team,awayTeam:g.away_team,kickoff:g.kickoff},snapshot)?.completed===true)})).sort((a,b)=>a.key-b.key);
 let active=covered.find(w=>!w.finished)?.key;
 if(active===undefined&&covered.length){const last=covered.at(-1).key;active=[...groups.keys()].filter(k=>k>last).sort((a,b)=>a-b)[0]??last;}
 if(active===undefined){
  // Legacy feed: hold the latest started week until every known fixture is confirmed final.
  const started=[...groups.entries()].filter(([,gs])=>gs.some(g=>Date.parse(g.kickoff)<=now)).sort((a,b)=>b[0]-a[0]);
  active=started[0]?.[0]??[...groups.keys()].sort((a,b)=>a-b)[0];
  if(active!==undefined&&groups.get(active)?.every(g=>matchTouchdownResult({homeTeam:g.home_team,awayTeam:g.away_team,kickoff:g.kickoff},snapshot)?.completed===true))active=[...groups.keys()].filter(k=>k>active).sort((a,b)=>a-b)[0]??active;
 }
 const visible=games.filter(g=>ordinal(g)===active||g.completed&&ordinal(g)<active);
 return {season:active===undefined?null:Math.floor(active/100),week:active===undefined?null:active%100,games:visible,hiddenGames:games.filter(g=>ordinal(g)>active).length,coverageConfirmed:covered.some(w=>w.key===active)};
}
export function weeklyTouchdownReport(report,archive,view){
 if(!report||view.week==null)return null;
 const ids=new Set(view.games.map(g=>g.game_id)),byId=new Map();
 for(const g of [...(archive?.games||[]),...(report.games||[])])if(ids.has(g.gameId))byId.set(g.gameId,g);
 return {...report,season:view.season??report.season,week:view.week??report.week,games:[...byId.values()].sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff))};
}
