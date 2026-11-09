import test from 'node:test';import assert from 'node:assert/strict';import {retainedGameOdds} from './retained-game-odds.mjs';import {teamNames,} from './market-core.mjs';
const game={game_id:'g',home_team:'ATL',away_team:'CIN',kickoff:'2026-11-08T18:00Z'},row={homeTeam:'Atlanta Falcons',awayTeam:'Cincinnati Bengals',kickoff:game.kickoff,bookKey:'dk',book:'DraftKings',source:'The Odds API',market:'totals',side:'Over',point:44.5,price:-110,observedAt:'2026-11-08T16:00Z',providerUpdatedAt:'2026-11-08T15:59Z'};
test('missing live events retain authentic prices and original timestamps without inventing freshness',()=>{
 const result=retainedGameOdds([],{observations:[row]},[game],teamNames);assert.equal(result.length,1);assert.equal(result[0].archived,true);assert.equal(result[0].bookmakers[0].markets[0].outcomes[0].point,44.5);assert.equal(result[0].bookmakers[0].observed_at,row.observedAt);
 assert.equal(retainedGameOdds([],{observations:[{...row,kickoff:'2026-11-15T18:00Z'}]},[game],teamNames).length,0);
});
test('Rams schedule aliases still recover old prices',()=>{
 const g={...game,home_team:'WAS',away_team:'LA'};
 const result=retainedGameOdds([],{observations:[{...row,homeTeam:'Washington Commanders',awayTeam:'Los Angeles Rams'}]},[g],teamNames);assert.equal(result.length,1);
});
