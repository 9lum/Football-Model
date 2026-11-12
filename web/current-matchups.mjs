/** Matchup Lab uses only the active NFL season/week, including that week's finals.
 * @param {any} view */
export function currentMatchups(view={}){
 if(view.season==null||view.week==null)return [];
 return (view.games||[]).filter(g=>Number(g.season)===Number(view.season)&&Number(g.week)===Number(view.week));
}
/** Old deep links and prior-week player forecasts must not select an archived game.
 * @param {any[]} games
 * @param {any} selectedId
 * @param {any} forecastId */
export function selectMatchup(games=[],selectedId,forecastId,now=Date.now()){
 return games.find(g=>g.game_id===selectedId)||games.find(g=>g.game_id===forecastId)||games.find(g=>!g.completed&&Date.parse(g.kickoff)>now)||games.at(-1);
}

/** Explicit historical selection; the default remains the active NFL week. */
export function matchupWeeks(view={}){
 const active=Number(view.season)*100+Number(view.week),weeks=new Map();
 for(const g of view.games||[]){const n=Number(g.season)*100+Number(g.week);if(!Number.isFinite(n)||n>active)continue;const key=g.season+'-'+g.week;weeks.set(key,{key,season:Number(g.season),week:Number(g.week)});}
 return [...weeks.values()].sort((a,b)=>b.season-a.season||b.week-a.week);
}
export function weekMatchups(view={},key=''){
 const selected=matchupWeeks(view).find(w=>w.key===key);
 return selected?currentMatchups({...view,...selected}):currentMatchups(view);
}
