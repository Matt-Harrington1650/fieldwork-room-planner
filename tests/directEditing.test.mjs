import {test} from 'node:test';
import assert from 'node:assert/strict';
import {seed,roomPoints,parseProject,footprint} from '../apps/web/src/domain.ts';
import {migrate} from '../apps/web/src/planner.ts';
import {dragWall,dragCorner,doorOnWall,resizeItem,setWallLength,splitWall,validOutline,reshapeRoom,edges} from '../apps/web/src/directEditing.ts';
const sample=()=>migrate(structuredClone(seed));

test('dragging a supporting wall moves attached equipment and preserves the original snapshot',()=>{
 const p=sample(),old=structuredClone(p),next=dragWall(p,2,0,304.8);
 assert.equal(next.room.depth,6304.8);assert.equal(next.equipment[1].y,p.equipment[1].y+304.8);
 assert.equal(next.equipment[4].y,p.equipment[4].y);assert.deepEqual(p,old);
 assert.equal(parseProject(JSON.stringify(next)).room.depth,6304.8);
});
test('moving a wall with locked attached equipment is rejected',()=>{
 const p=sample();p.equipment[1].locked=true;
 assert.throws(()=>dragWall(p,2,0,304.8),/Unlock ATS-1/);
});
test('corner drag preserves square adjacent walls and rejects inverted or collapsed rooms',()=>{
 const p=sample(),next=dragCorner(p,2,304.8,609.6),ps=roomPoints(next);
 assert.deepEqual(ps,[[0,0],[8304.8,0],[8304.8,6609.6],[0,6609.6]]);
 assert.throws(()=>dragWall(p,2,0,-7000));
 assert.equal(validOutline([[0,0],[1000,1000],[0,1000],[1000,0]]),false);
});
test('origin changes translate references, regions, holes and free objects together',()=>{
 const p=sample();p.underlay={name:'plan',data:'data:image/png;base64,AA',x:0,y:0,width:8000,height:6000,opacity:.5,locked:true,rotation:0,calibrated:true};p.regions=[{id:'r',name:'future',kind:'future',x:500,y:500,width:500,depth:500,hard:true}];p.room.holes=[[[2000,2000],[2500,2000],[2500,2500],[2000,2500]]];
 const next=dragWall(p,3,-304.8,0);
 assert.equal(next.room.width,8304.8);assert.equal(next.underlay.x,304.8);assert.equal(next.regions[0].x,804.8);assert.equal(next.room.holes[0][0][0],2304.8);
 assert.equal(next.room.obstacles[0].x,p.room.obstacles[0].x+304.8);
});
test('room walls cannot cross a hole',()=>{const p=sample();p.room.holes=[[[1000,1000],[2000,1000],[2000,2000],[1000,2000]]];assert.throws(()=>dragWall(p,3,1500,0),/hole/);});
test('door dragging projects to a wall, clamps its opening and changes orientation',()=>{
 const p=sample(),d=p.room.doors[0],next=doorOnWall(p,d,[7990,5900],25.4);
 assert.equal(next.x,8000);assert.equal(next.angle,90);assert.equal(next.y,4900);
 const shifted=dragWall(p,0,0,-304.8);assert.equal(shifted.room.doors[0].y,0);assert.equal(shifted.room.depth,6304.8);
});
test('exact wall length and split-wall jogs remain valid',()=>{
 const p=sample(),wide=setWallLength(p,0,9144);assert.equal(wide.room.width,9144);
 const split=splitWall(p,2),jog=dragWall(split,2,0,304.8);
 assert.equal(validOutline(roomPoints(jog)),true);assert.equal(roomPoints(jog).length,6);
 assert.equal(edges(jog).some(e=>Math.abs(e.length-304.8)<.01),true);
});
for(const rotation of [0,90,180,270])test('resize corner preserves the opposite corner at rotation '+rotation,()=>{
 const e={...sample().equipment[0],rotation},r=footprint(e),next=resizeItem(e,0,-304.8,-152.4),n=footprint(next);
 assert.ok(Math.abs(n.x+n.w-r.x-r.w)<.001);assert.ok(Math.abs(n.y+n.h-r.y-r.h)<.001);
 assert.equal(n.w,r.w+304.8);assert.equal(n.h,r.h+152.4);
 assert.equal(resizeItem({...e,locked:true},0,300,300).width,e.width);
});

test('wall movement keeps an attached assembly rigid and rejects conflicting supports',()=>{
 const p=sample();p.equipment[1].group='lineup';p.equipment.push({...p.equipment[1],id:'FREE',x:3000,y:3000,wall:'any',group:'lineup'});
 const next=dragWall(p,2,0,304.8);assert.equal(next.equipment.at(-1).y,p.equipment.at(-1).y+304.8);
 p.equipment.at(-1).locked=true;assert.throws(()=>dragWall(p,2,0,304.8),/complete assembly/);
 const corner=sample();corner.equipment[1].group='corner';corner.equipment[4].group='corner';assert.throws(()=>dragWall(corner,2,0,304.8),/different directions/);
});
