import test from 'node:test';
import assert from 'node:assert/strict';
import {propActualIndex,propActual} from './prop-actuals.mjs';
test('actuals match both player and game, preserve zero and leave missing stats unknown',()=>{
 const row={playerId:'p',gameId:'g',completed:true,basic:{receiving_yards:82,receptions:6,receiving_tds:0}};
 const index=propActualIndex({rows:[row]});
 assert.equal(propActual(index.get('p|g'),'player_reception_yds').value,82);
 assert.equal(propActual(index.get('p|g'),'player_reception_tds').value,0);
 assert.equal(propActual(index.get('p|next'),'player_reception_yds'),null);
 assert.equal(propActual(row,'player_pass_yds'),null);
});
test('newer corrected box scores win regardless of row order',()=>{
 const a={playerId:'p',gameId:'g',observedAt:'2026-11-15T23:00Z',basic:{carries:15}},b={...a,observedAt:'2026-11-16T00:00Z',basic:{carries:16}};
 assert.equal(propActual(propActualIndex({rows:[b,a]}).get('p|g'),'player_rush_attempts').value,16);
});
test('all tracked prop fields map to actuals without substituting absent values',()=>{
 const basic={targets:9,receiving_yards:80,receptions:6,receiving_tds:1,rushing_yards:21,carries:4,rushing_tds:0,passing_yards:220,attempts:30,completions:20,passing_tds:2,passing_interceptions:1};
 for(const [market,key] of Object.entries({player_targets:'targets',player_reception_yds:'receiving_yards',player_receptions:'receptions',player_reception_tds:'receiving_tds',player_rush_yds:'rushing_yards',player_rush_attempts:'carries',player_rush_tds:'rushing_tds',player_pass_yds:'passing_yards',player_pass_attempts:'attempts',player_pass_completions:'completions',player_pass_tds:'passing_tds',player_pass_interceptions:'passing_interceptions'}))assert.equal(propActual({basic},market).value,basic[key]);
});
