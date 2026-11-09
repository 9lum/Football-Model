import test from 'node:test';import assert from 'node:assert/strict';import {matchupWeek,eventInGames,weeklyTouchdownReport} from './matchup-week.mjs';
const sun={game_id:'2026_09_ARI_SEA',season:2026,week:9,home_team:'SEA',away_team:'ARI',kickoff:'2026-11-08T21:25Z',completed:true};
const mon={game_id:'2026_09_BUF_MIN',season:2026,week:9,home_team:'MIN',away_team:'BUF',kickoff:'2026-11-10T01:15Z'};
const next={game_id:'2026_10_WAS_NYG',season:2026,week:10,home_team:'NYG',away_team:'WAS',kickoff:'2026-11-13T01:15Z'};
const final=g=>({id:g.game_id,homeTeam:g.home_team,awayTeam:g.away_team,kickoff:g.kickoff,completed:true});
const snapshot={weekCoverage:[{season:2026,week:9,eventIds:[sun.game_id,mon.game_id]},{season:2026,week:10,eventIds:[next.game_id]}],results:[final(sun),{...final(mon),completed:false},{...final(next),completed:false}]};
test('Sunday and Monday kickoff do not unlock next week; Monday confirmed final does',()=>{
 for(const now of ['2026-11-09T00:00Z','2026-11-10T03:00Z']){
  const view=matchupWeek([sun,mon,next],snapshot,Date.parse(now));assert.equal(view.week,9);assert.ok(!view.games.includes(next));assert.equal(eventInGames({home_team:'New York Giants',away_team:'Washington Commanders',commence_time:next.kickoff},view.games),false);
 }
 const finished={...snapshot,results:[final(sun),final(mon),{...final(next),completed:false}]};assert.equal(matchupWeek([sun,mon,next],finished,Date.parse('2026-11-10T05:00Z')).week,10);
});
test('missing finals and postponed Monday games hold the entire prior week',()=>{
 const missing={...snapshot,results:[final(sun),{...final(next),completed:false}]};assert.equal(matchupWeek([sun,mon,next],missing,Date.parse('2026-11-13T02:00Z')).week,9);
});
test('legacy snapshots stay on the current week and archived TD picks remain accessible',()=>{
 const view=matchupWeek([sun,mon,next],{results:[final(sun)]},Date.parse('2026-11-09T00:00Z'));assert.equal(view.week,9);
 const report=weeklyTouchdownReport({season:2026,week:10,games:[{gameId:next.game_id,kickoff:next.kickoff}]},{games:[{gameId:sun.game_id,kickoff:sun.kickoff}]},view);assert.equal(report.week,9);assert.equal(report.games[0].gameId,sun.game_id);
});
test('a partial coverage response cannot unlock next week while a known Monday fixture remains unfinished',()=>{
 const partial={...snapshot,weekCoverage:[{season:2026,week:9,eventIds:[sun.game_id]}]};
 assert.equal(matchupWeek([sun,mon,next],partial,Date.parse('2026-11-10T02:00Z')).week,9);
});
test('a finished week remains visible Monday evening until Tuesday midnight Eastern',()=>{
 const done={...snapshot,results:[final(sun),final(mon),{...final(next),completed:false}]};
 assert.equal(matchupWeek([sun,mon,next],done,Date.parse('2026-11-10T04:59:00Z')).week,9);
 assert.equal(matchupWeek([sun,mon,next],done,Date.parse('2026-11-10T05:00:00Z')).week,10);
});
