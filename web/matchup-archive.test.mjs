import test from 'node:test';import assert from 'node:assert/strict';
import {archivedMatchup,mergeMatchupBundle} from './matchup-archive.mjs';
const f={gameId:'2026_09_CIN_ATL',playerId:'p',kickoff:'2026-11-08T18:00Z',marketSamples:{player_reception_yds:{values:[40,50,60]}}};
const a={kind:'published_pregame',gameId:f.gameId,kickoff:f.kickoff,issuedAt:'2026-11-08T17:00Z',sourceCommit:'abc',bundle:{forecasts:[f],players:[{playerId:'p',team:'ATL',history:[{gameId:'old',week:8}]}]}};
test('retains original pregame draws and joins later actual history without changing team or forecast',()=>{
 const current={healthSnapshot:{week:10},forecasts:[{playerId:'p',gameId:'next',marketSamples:{}}],players:[{playerId:'p',team:'SEA',history:[{gameId:f.gameId,week:9,receiving_yards:56}]}]};
 const archive=archivedMatchup(a,f.gameId),merged=mergeMatchupBundle(current,{...archive.bundle,healthSnapshot:{week:9}},f.gameId);
 assert.deepEqual(merged.forecasts.find(v=>v.gameId===f.gameId).marketSamples,f.marketSamples);assert.equal(merged.healthSnapshot.week,9);assert.equal(merged.players[0].team,'ATL');assert.equal(merged.players[0].history.length,2);
});
test('rejects post-kickoff publications and cross-game archive substitutions',()=>{
 assert.equal(archivedMatchup({...a,issuedAt:'2026-11-08T18:01Z'},f.gameId),null);assert.equal(archivedMatchup(a,'other'),null);assert.equal(archivedMatchup({...a,bundle:{forecasts:[{...f,gameId:'other'}]}},f.gameId),null);
});
