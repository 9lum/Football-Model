import test from 'node:test';
import assert from 'node:assert/strict';
import {sortPlayerResults} from './performance.mjs';
test('closest and furthest rank numeric absolute error and keep unknown outcomes last',()=>{
 const rows=[{id:'pending',projected:0,actual:null},{id:'large',projected:12,actual:0},{id:'negative',projected:0,actual:3},{id:'exact',projected:0,actual:0},{id:'missing',actual:0}];
 assert.deepEqual(sortPlayerResults(rows,'closest').map(r=>r.id),['exact','negative','large','missing','pending']);
 assert.deepEqual(sortPlayerResults(rows,'furthest').map(r=>r.id),['large','negative','exact','missing','pending']);
 assert.equal(rows[0].id,'pending');
});
test('probability error orders events and non-events consistently with Brier error',()=>{
 const rows=[{id:'wrong',projected:.9,actual:0},{id:'right',projected:.9,actual:1},{id:'other',projected:.2,actual:0}];
 assert.deepEqual(sortPlayerResults(rows,'closest').map(r=>r.id),['right','other','wrong']);
});
