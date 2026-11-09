import test from 'node:test';import assert from 'node:assert/strict';
import {touchdownGameState} from './touchdown-game-state.mjs';
const game={homeTeam:'ATL',awayTeam:'CIN',kickoff:'2026-11-08T18:00:00Z',status:'upcoming'},now=Date.parse('2026-11-08T17:00Z');
const result={homeTeam:'Atlanta Falcons',awayTeam:'Cincinnati Bengals',kickoff:game.kickoff,completed:true,homeScore:14,awayScore:24,observedAt:'2026-11-08T22:00Z'};
test('confirmed final highlights actual winner, with ties and zero scores handled',()=>{
 assert.equal(touchdownGameState(game,{results:[result]},now).winner,'CIN');
 assert.equal(touchdownGameState(game,{results:[{...result,awayScore:0}]},now).winner,'ATL');
 const tie=touchdownGameState(game,{results:[{...result,awayScore:14}]},now);assert.equal(tie.winner,null);assert.equal(tie.label,'Finished · Tie');
});
test('scores, elapsed kickoff and other fixtures never imply a confirmed final',()=>{
 for(const r of [{...result,completed:false,state:'in'},{...result,awayScore:null},{...result,kickoff:'2026-11-15T18:00Z'},{...result,homeTeam:'KC'}])assert.notEqual(touchdownGameState(game,{results:[r]},now).status,'finished');
 assert.equal(touchdownGameState(game,{},now).status,'upcoming');
 assert.equal(touchdownGameState(game,{},now+7200000).status,'started');
});

test('in-progress games carry scores and clock, then switch to finished on a confirmed final',()=>{
 const live={...result,completed:false,state:'in',detail:'Q4 0:18'};
 const state=touchdownGameState(game,{results:[live]},now);
 assert.equal(state.status,'in-progress');assert.equal(state.detail,'Q4 0:18');assert.equal(state.awayScore,24);assert.equal(state.winner,null);
 assert.equal(touchdownGameState(game,{results:[{...live,completed:true,state:'post'}]},now).status,'finished');
});
test('scorer glow requires a unique player on the correct team in the exact game',async()=>{
 const {touchdownScored}=await import('./touchdown-game-state.mjs');
 const p={name:'Player One',team:'CIN'},scorer={name:'Player One',team:'Cincinnati Bengals',touchdowns:2};
 const snapshot={results:[{...result,scorers:[scorer]}]};
 assert.equal(touchdownScored(p,game,snapshot),2);
 assert.equal(touchdownScored({...p,team:'ATL'},game,snapshot),null);
 assert.equal(touchdownScored(p,{...game,kickoff:'2026-11-15T18:00Z'},snapshot),null);
 assert.equal(touchdownScored(p,game,{results:[{...result,scorers:[scorer,scorer]}]}),null);
 assert.equal(touchdownScored(p,game,{results:[{...result,scorers:[]}]}),null);
});
