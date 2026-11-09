import test from 'node:test';import assert from 'node:assert/strict';import {siteGames} from './site-games.mjs';import {matchupResult} from './matchup-result.mjs';
test('completed archived games survive an upcoming-only schedule and kickoff discrepancies',()=>{
 const p={gameId:'2026_09_LV_SF',homeTeam:'SF',awayTeam:'LV',kickoff:'2026-11-08T21:05Z',projectedAt:'2026-11-08T18:00Z',probHomeWin:.7,probAwayWin:.3};
 const snapshot={results:[{id:'espn-1',homeTeam:'San Francisco 49ers',awayTeam:'Las Vegas Raiders',kickoff:'2026-11-08T21:25Z',completed:true,homeScore:24,awayScore:14}]};
 const games=siteGames([],{projections:[p]}, {},snapshot);assert.equal(games.length,1);assert.equal(games[0].completed,true);assert.equal(matchupResult(games[0],snapshot,{projections:[p]}).checks[0].tone,'good');
});
test('completed games without a saved projection show the final without fabricated model grades',()=>{
 const snapshot={results:[{id:'espn-2',homeTeam:'Seattle Seahawks',awayTeam:'Arizona Cardinals',kickoff:'2026-11-08T21:25Z',completed:true,homeScore:24,awayScore:14}]};
 const games=siteGames([],{}, {},snapshot);assert.equal(games.length,1);assert.equal(matchupResult(games[0],snapshot,{}).projection,null);
});
