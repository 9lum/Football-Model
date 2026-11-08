import test from 'node:test';
import assert from 'node:assert/strict';
import {touchdownTeamPicks} from './touchdown-picks.mjs';
const player=(id,team,probability,extra={})=>({playerId:id,name:id,team,probability,position:'WR',...extra});
test('both offenses get independent top-three rankings even when all global candidates belong to one team',()=>{
 const game={awayTeam:'CIN',homeTeam:'ATL',players:[player('a','CIN',.8),player('b','CIN',.7),player('c','CIN',.6),player('d','CIN',.5),player('e','ATL',.4),player('f','ATL',.3),player('g','ATL',.2)],candidates:[player('a','CIN',.8)]};
 const groups=touchdownTeamPicks(game);
 assert.deepEqual(groups.map(g=>g.players.map(p=>p.playerId)),[['a','b','c'],['e','f','g']]);
 assert.equal(groups[1].players[0].risk,'Team leader · highest estimated probability');
});
test('filters, exclusions and missing team data never substitute players from the other team',()=>{
 const game={awayTeam:'CIN',homeTeam:'ATL',players:[player('out','ATL',.9,{health:{status:'OUT'}}),player('rb','ATL',.4,{position:'RB'}),player('wr','CIN',.3)]};
 assert.deepEqual(touchdownTeamPicks(game,{position:'WR'}).map(g=>g.players.map(p=>p.playerId)),[['wr'],[]]);
 assert.deepEqual(touchdownTeamPicks(game,{search:'rb'}).map(g=>g.players.map(p=>p.playerId)),[[],['rb']]);
});
test('fresh injury registry overrides older TD report and backfills the next eligible scorer',()=>{
 const game={awayTeam:'CIN',homeTeam:'ATL',players:[player('a','CIN',.8),player('b','CIN',.7),player('c','CIN',.6),player('d','CIN',.5)]};
 const currentPlayers=[player('a','CIN',.8,{health:{status:'OUT'}})];
 assert.deepEqual(touchdownTeamPicks(game,{currentPlayers})[0].players.map(p=>p.playerId),['b','c','d']);
 currentPlayers[0].health={status:'QUESTIONABLE'};
 assert.equal(touchdownTeamPicks(game,{currentPlayers})[0].players[0].playerId,'a');
 currentPlayers[0].health={status:'OUT',scopeMismatch:true};
 assert.equal(touchdownTeamPicks(game,{currentPlayers})[0].players[0].playerId,'a');
});
