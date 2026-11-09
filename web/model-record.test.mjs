import test from 'node:test';import assert from 'node:assert/strict';import {filterRecord,summarizeRecord} from './model-record.mjs';import {parseResearchRoute,researchHref} from './research-links.mjs';
test('season, week and market scopes combine without counting pending or ungraded as losses',()=>{
 const rows=[{season:2026,week:9,market:'total',status:'win'},{season:2026,week:9,market:'total',status:'push'},{season:2026,week:9,market:'total',status:'pending'},{season:2026,week:9,market:'total',status:'ungraded'},{season:2025,week:9,market:'total',status:'loss'},{season:2026,week:8,market:'moneyline',status:'loss'}];
 const s=summarizeRecord(filterRecord(rows,'2026','9','total'));assert.equal(s.hitRate,1);assert.equal(s.losses,0);assert.equal(s.pushes,1);assert.equal(s.pending,1);assert.equal(s.ungraded,1);assert.equal(summarizeRecord([]).hitRate,null);
});
test('record tab supports direct links and browser routing',()=>{assert.equal(researchHref('record'),'#record');assert.equal(parseResearchRoute('#record').page,'record');});
