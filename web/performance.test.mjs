import test from 'node:test';import assert from 'node:assert/strict';import {performanceMetrics,performanceRows} from './performance.mjs';
test('error and baseline skill use paired observations only, with explicit bias direction',()=>{
 const rows=[{scope:'published',season:2026,week:9,gameId:'g1',type:'continuous',projected:12,actual:10,baseline:15,p10:5,p90:15},{scope:'published',season:2026,week:9,gameId:'g2',type:'continuous',projected:20,actual:10}];
 const m=performanceMetrics(rows);assert.equal(m.mae,6);assert.equal(m.bias,6);assert.equal(m.pairedN,1);assert.equal(m.pairedModelMae,2);assert.equal(m.baselineMae,5);assert.equal(m.skill,.6);assert.equal(m.coverage80,1);assert.equal(m.intervalN,1);
 assert.equal(performanceRows(rows,{week:'8'}).length,0);
});
test('Brier, calibration and >=70% cohort do not use missing outcomes',()=>{
 const m=performanceMetrics([{gameId:'g',type:'probability',projected:.8,actual:1},{gameId:'g',type:'probability',projected:.2,actual:0},{gameId:'g',type:'probability',projected:.9,actual:null}]);
 assert.ok(Math.abs(m.brier-.04)<1e-9);assert.equal(m.n,2);assert.equal(m.games,1);assert.equal(m.high70N,1);assert.equal(m.high70Rate,1);assert.equal(m.pending,1);
});
test('CSV keeps quoted names, missing actuals and numeric negative residual-related values intact',async()=>{
 const {performanceCsv}=await import('./performance.mjs');const csv=performanceCsv([{entity:'Player, "One"',projected:-2,actual:null}]);assert.ok(csv.includes('"Player, ""One"""'));assert.ok(csv.includes('"-2"'));assert.ok(!csv.includes('undefined'));
});
