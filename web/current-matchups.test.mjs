import test from 'node:test';import assert from 'node:assert/strict';
import {currentMatchups,selectMatchup} from './current-matchups.mjs';
const old={game_id:'2026_09_BUF_MIN',season:2026,week:9,completed:true,kickoff:'2026-11-10T01:15Z'},thu={game_id:'2026_10_WAS_NYG',season:2026,week:10,kickoff:'2026-11-13T01:15Z'},sun={game_id:'2026_10_MIN_GB',season:2026,week:10,kickoff:'2026-11-15T18:00Z'};
test('only the active season/week is selectable, retaining current-week finals',()=>{
 const done={...thu,completed:true},games=[old,done,sun,{...sun,season:2025},{...sun,week:11}];
 assert.deepEqual(currentMatchups({season:2026,week:10,games}),[done,sun]);assert.equal(games.length,5);
});
test('stale deep links and old forecast IDs fall back to a current-week game',()=>{
 const choices=currentMatchups({season:2026,week:10,games:[old,thu,sun]});
 assert.equal(selectMatchup(choices,old.game_id,old.game_id,Date.parse('2026-11-12T18:00Z')),thu);
 assert.equal(selectMatchup(choices,sun.game_id,old.game_id),sun);
 assert.equal(selectMatchup([],old.game_id,old.game_id),undefined);
 assert.deepEqual(currentMatchups({games:[old]}),[]);
});
