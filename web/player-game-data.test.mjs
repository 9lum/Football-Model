import test from 'node:test';import assert from 'node:assert/strict';
import {mergePlayerGames,mergeActualsIntoBundle,mergeFinalResults,playerTrendOption,availablePlayerMarkets} from './player-game-data.mjs';
const gid='2026_09_BUF_MIN',g={gameId:gid,season:2026,week:9,kickoff:'2026-11-10T01:15Z',team:'MIN',opponent:'BUF'};
test('fresh final actuals update all histories and card totals without mutating model forecasts',()=>{
 const base={season:2026,players:[{playerId:'p',team:'MIN',season:2026,position:'QB',history:[{...g,passing_yards:70,attempts:25,completions:8}]}],forecasts:[{playerId:'p',marketSamples:{player_pass_yds:{values:[193]}}}]};
 const recent={generatedAt:'2026-11-10T05:30Z',rows:[{...g,playerId:'p',basic:{passing_yards:81,attempts:25,completions:8},observedAt:'2026-11-10T05:30Z'},{...g,playerId:'new',name:'New QB',position:'QB',basic:{passing_yards:58},observedAt:'2026-11-10T05:30Z'}]};const result=mergeActualsIntoBundle(base,recent);assert.equal(result.players[0].history[0].passing_yards,81);assert.equal(result.players[0].basicStats.season.passing_yards,81);assert.equal(result.players[1].actualOnly,true);assert.equal(base.players[0].history[0].passing_yards,70);assert.deepEqual(result.forecasts,base.forecasts);
});
test('later primary corrections take precedence while missing values never become zero',()=>{
 const rows=mergePlayerGames([],{generatedAt:'2026-11-10T06:00Z',games:[{...g,basic:{passing_yards:82}}]},[{...g,basic:{passing_yards:81,passing_tds:0},observedAt:'2026-11-10T05:30Z'}]);assert.equal(rows[0].passing_yards,82);assert.deepEqual(rows[0].statDiscrepancies,[{stat:"passing_yards",espn:81,nflverse:82}]);assert.equal(rows[0].passing_tds,0);assert.equal(rows[0].attempts,undefined);
});
test('hover shows both exact actual and real saved projection, with unavailable forecasts clearly labeled',()=>{
 const archive={kind:'published_pregame',gameId:gid,kickoff:g.kickoff,issuedAt:'2026-11-09T19:00Z',sourceCommit:'verified',bundle:{season:2026,generatedAt:'2026-11-09T18:00Z',players:[{playerId:'p',name:'QB',team:'MIN',position:'QB'}],forecasts:[{...g,homeTeam:'MIN',awayTeam:'BUF',playerId:'p',name:'QB',position:'QB',features:{attempts_last3:30},marketSamples:{player_pass_yds:{values:[190,196],validationPassed:false}}}]}};
 const option=playerTrendOption({games:[{...g,passing_yards:81}],archives:{[gid]:archive},playerId:'p',market:'player_pass_yds',target:'passing_yards'});const html=option.tooltip.formatter([{dataIndex:0}]);assert.match(html,/Actual: <b>81/);assert.match(html,/Published pregame projection: <b>193/);assert.match(html,/-112/);assert.deepEqual(option.series[1].data,[193]);
 const missing=playerTrendOption({games:[{...g,passing_yards:0}],playerId:'p',market:'player_pass_yds',target:'passing_yards'}).tooltip.formatter([{dataIndex:0}]);assert.match(missing,/Actual: <b>0/);assert.match(missing,/Not archived/);
});
test('actual-only players have position-appropriate market menus and finals enrich scoreboard evidence',()=>{
 assert.ok(availablePlayerMarkets({position:'QB'},null,[{passing_yards:58,attempts:7,receptions:0}]).includes('player_pass_yds'));assert.ok(!availablePlayerMarkets({position:'QB'},null,[{passing_yards:58,receptions:0}]).includes('player_receptions'));
 const merged=mergeFinalResults({results:[{id:'game',completed:false}],data:[]},{games:[{id:'game',completed:true,homeScore:3,awayScore:24}]});assert.equal(merged.results[0].completed,true);assert.deepEqual(merged.data,[]);
});
