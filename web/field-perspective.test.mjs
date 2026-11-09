import test from 'node:test';
import assert from 'node:assert/strict';
import {fieldPoint,fieldPolygon,fieldBands} from './field-perspective.mjs';
test('end-zone camera has real perspective and flat view remains overhead',()=>{
 const width=(z,depth)=>fieldPoint(100,z,depth).x-fieldPoint(0,z,depth).x;
 assert.ok(width(58,true)<width(8,true)*.65);
 assert.equal(width(58,false),width(8,false));
 assert.ok(fieldPoint(50,58,true).y<fieldPoint(50,8,true).y);
 assert.notEqual(fieldPolygon(0,0,100,64,true),fieldPolygon(0,0,100,64,false));
});
test('all twelve projected zones keep gutters, positive area, and fit the view box',()=>{
 for(const depth of [true,false])for(const yaw of [-5,0,5])for(const [near,far] of Object.values(fieldBands)){
  for(let i=0;i<3;i++){
   const x=7+i*29.5,points=fieldPolygon(x,near+1.2,x+27,far-1.2,depth,yaw).split(' ').map(p=>p.split(',').map(Number));
   assert.ok(points.every(([x,y])=>x>0&&x<720&&y>0&&y<480));
   assert.ok(points[0][1]>points[3][1]);
   if(i<2)assert.ok(fieldPoint(x+27,near+1.2,depth,yaw).x<fieldPoint(x+29.5,near+1.2,depth,yaw).x);
  }
 }
});
