import test from 'node:test';import assert from 'node:assert/strict';import {matchupResult} from './matchup-result.mjs';
const game={game_id:'g',home_team:'ATL',away_team:'CIN',kickoff:'2026-11-08T18:00Z'};
const result={homeTeam:'Atlanta Falcons',awayTeam:'Cincinnati Bengals',kickoff:game.kickoff,completed:true,homeScore:14,awayScore:24};
const p={gameId:'g',homeTeam:'ATL',awayTeam:'CIN',kickoff:game.kickoff,projectedAt:'2026-11-08T17:00Z',homePoints:17,awayPoints:24,probHomeWin:.3,probAwayWin:.7,totalInterval80:[30,50],marginInterval80:[-14,3]};
test('verified pregame winner and intervals grade green or red against confirmed final',()=>{
 let r=matchupResult(game,{results:[result]},{projections:[p]});assert.deepEqual(r.checks.map(c=>c.tone),['good','good','good']);
 r=matchupResult(game,{results:[{...result,homeScore:60}]},{projections:[p]});assert.deepEqual(r.checks.map(c=>c.tone),['bad','bad','bad']);
});
test('unconfirmed games and after-kickoff forecasts cannot receive a retrospective grade',()=>{
 assert.equal(matchupResult(game,{results:[{...result,completed:false,state:'in'}]},{projections:[p]}),null);
 assert.equal(matchupResult(game,{results:[result]},{projections:[{...p,projectedAt:'2026-11-08T19:00Z'}]}).projection,null);
 assert.equal(matchupResult(game,{results:[{...result,homeScore:24}]},{projections:[p]}).checks[0].tone,'neutral');
});
