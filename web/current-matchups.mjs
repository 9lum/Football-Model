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
