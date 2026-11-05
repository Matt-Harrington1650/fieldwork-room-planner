import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
// React's DOM event feature detection must run with a browser document present.
const initialDom=new JSDOM('<!doctype html><div></div>',{url:'http://127.0.0.1:8765'});
globalThis.window=initialDom.window;globalThis.document=initialDom.window.document;
const {createRoot}=await import('react-dom/client');
const require=createRequire(import.meta.url);
const bundle=await build({entryPoints:[fileURLToPath(new URL('../apps/web/src/App.tsx',import.meta.url))],bundle:true,write:false,format:'esm',platform:'node',loader:{'.css':'empty'},plugins:[{name:'shared-react',setup(builder){builder.onResolve({filter:/^(react|lucide-react)(\/.*)?$/},args=>({path:pathToFileURL(require.resolve(args.path)).href,external:true}));}}]});
const {App,NumberField,LengthField}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
function setup(){
 const dom=new JSDOM('<!doctype html><div id="root"></div>',{url:'http://127.0.0.1:8765'});
 globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.localStorage=dom.window.localStorage;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 globalThis.fetch=async()=>{throw Error('offline test')};
 const proto=dom.window.SVGElement.prototype;
 proto.getScreenCTM=()=>({inverse:()=>({})});
 proto.createSVGPoint=()=>({x:0,y:0,matrixTransform(){return{x:this.x,y:this.y}}});
 proto.setPointerCapture=()=>{};
 return {dom,root:createRoot(document.getElementById('root'))};
}
async function event(target,type,values={}){await act(async()=>{target.dispatchEvent(new window.MouseEvent(type,{bubbles:true,button:0,...values}));});}
function button(title){return document.querySelector(`button[title="${title}"]`);}
function saved(){return JSON.parse(localStorage.getItem('fieldwork-project'));}
test('drag release does not crash; multiple drags have distinct undo/redo snapshots',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));
 const original=saved();
 for(let i=0;i<2;i++){
 const shape=document.querySelector('.equipment-shape'),canvas=document.querySelector('.plan-canvas');
 await event(shape,'pointerdown',{clientX:100,clientY:100});
 await event(canvas,'pointermove',{clientX:125,clientY:150});
 await event(canvas,'pointerup',{clientX:125,clientY:150});
 assert.ok(document.querySelector('h1'),'editor remains mounted after drag');
 }
 const first=original.equipment[0].x+25.4;
 const second=Math.round((first+25.4)*1e6)/1e6;
 assert.equal(saved().equipment[0].x,second);
 await event(button('Undo'),'click');assert.equal(saved().equipment[0].x,first);
 await event(button('Undo'),'click');assert.equal(saved().equipment[0].x,original.equipment[0].x);
 await event(button('Redo'),'click');assert.equal(saved().equipment[0].x,first);
 }finally{await act(async()=>root.unmount());}
});
test('imperial field accepts fractions exactly and does not change a dimension on unchanged blur',async()=>{
 const {root}=setup();const changes=[];
 try{
 await act(async()=>root.render(React.createElement(LengthField,{value:1800,onValue:v=>changes.push(v)})));
 const input=document.querySelector('input');await event(input,'focusout');assert.deepEqual(changes,[],'rounded display must not alter canonical geometry');
 const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
 await act(async()=>{setter.call(input,`3' 6 1/2"`);input.dispatchEvent(new window.Event('input',{bubbles:true}));});
 await event(input,'focusout');assert.deepEqual(changes,[1079.5]);
 }finally{await act(async()=>root.unmount());}
});
test('all rendered lengths and area use imperial, including migrated saved projects',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));
 assert.ok(!/\bmm\b|m²|Millimeters/.test(document.body.textContent));
 assert.ok(document.body.textContent.includes('ft²'));
 assert.ok(document.body.textContent.includes('Feet & inches'));
 assert.equal(saved().units,'ft');
 }finally{await act(async()=>root.unmount());}
});
test('pointer cancellation and lost capture finalize once and leave the editor usable',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));
 const canvas=document.querySelector('.plan-canvas');
 await event(document.querySelector('.equipment-shape'),'pointerdown',{clientX:0,clientY:0});
 await event(canvas,'pointermove',{clientX:50,clientY:0});
 await event(canvas,'pointercancel');await event(canvas,'lostpointercapture');
 await event(button('Undo'),'click');assert.equal(saved().equipment[0].x,600);
 assert.equal(button('Undo').disabled,true,'only one undo entry');
 }finally{await act(async()=>root.unmount());}
});
test('ordinary button edits preserve original undo snapshots',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));
 await event(button('Rotate · R'),'click');assert.equal(saved().equipment[0].rotation,270);
 await event(button('Rotate · R'),'click');assert.equal(saved().equipment[0].rotation,0);
 await event(button('Undo'),'click');assert.equal(saved().equipment[0].rotation,270);
 await event(button('Undo'),'click');assert.equal(saved().equipment[0].rotation,180);
 }finally{await act(async()=>root.unmount());}
});
test('numeric edits accept a complete value before enforcing minimums; empty input restores its value',async()=>{
 const {root}=setup();const changes=[];
 try{
 await act(async()=>root.render(React.createElement(NumberField,{value:8000,min:4400,onValue:v=>changes.push(v)})));
 const input=document.querySelector('input');
 // Simulate native typing by invoking React's input value tracker through a real DOM event.
 const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
 await act(async()=>{setter.call(input,'1');input.dispatchEvent(new window.Event('input',{bubbles:true}));input.dispatchEvent(new window.Event('change',{bubbles:true}));});
 assert.equal(changes.length,0,'partial typing must not commit a clamped value');
 await act(async()=>{setter.call(input,'10000');input.dispatchEvent(new window.Event('input',{bubbles:true}));input.dispatchEvent(new window.Event('change',{bubbles:true}));});
 assert.equal(changes.length,0);
 await event(input,'focusout');
 assert.deepEqual(changes,[10000],'completed text is committed on blur');
 await act(async()=>{setter.call(input,'');input.dispatchEvent(new window.Event('input',{bubbles:true}));});
 await event(input,'focusout');
 assert.equal(input.value,'8000','an empty required field restores the last committed prop');
 assert.deepEqual(changes,[10000],'clearing does not commit zero');
 }finally{await act(async()=>root.unmount());}
});

test('blank project preserves the previous complete design across later edits and restores it',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));
 const original=saved();localStorage.setItem('fieldwork-server-project','123');
 await event(button('New blank project'),'click');
 const name=document.querySelector('[aria-label="New project name"]');
 const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
 await act(async()=>{setter.call(name,'My new design');name.dispatchEvent(new window.Event('input',{bubbles:true}));});
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Start blank project'),'click');
 const blank=saved();
 assert.equal(blank.name,'My new design');assert.equal(blank.units,'ft');assert.equal(blank.room.defined,false);assert.equal(document.querySelector('.room-boundary'),null);assert.equal(document.querySelector('.plan-dims'),null);assert.ok(document.querySelector('.empty-room-choices'));
 assert.equal(blank.room.width,6096);assert.equal(blank.room.depth,4876.8);
 assert.deepEqual(blank.equipment,[]);assert.deepEqual(blank.room.doors,[]);
 assert.deepEqual(blank.room.obstacles,[]);assert.deepEqual(blank.scenarios,[]);
 assert.deepEqual(blank.definitions,original.definitions);
 assert.equal(localStorage.getItem('fieldwork-server-project'),null);
 const projectName=document.querySelector('[aria-label="Project name"]');
 await act(async()=>{setter.call(projectName,'Edited new design');projectName.dispatchEvent(new window.Event('input',{bubbles:true}));});
 assert.deepEqual(JSON.parse(localStorage.getItem('fieldwork-before-new-project')).project,original);
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Scenarios'),'click');
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Restore previous project'),'click');
 assert.deepEqual(saved(),original);assert.equal(localStorage.getItem('fieldwork-server-project'),'123');
 }finally{await act(async()=>root.unmount());}
});

test('blank project does not clear the current design when its backup cannot be stored',async()=>{
 const {root}=setup();const storagePrototype=Object.getPrototypeOf(localStorage),originalSet=storagePrototype.setItem;
 try{
 await act(async()=>root.render(React.createElement(App)));const original=saved();
 storagePrototype.setItem=function(key,value){if(key==='fieldwork-before-new-project')throw Error('storage full');return originalSet.call(this,key,value);};
 await event(button('New blank project'),'click');
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Start blank project'),'click');
 assert.deepEqual(saved(),original);assert.ok(document.body.textContent.includes('Could not back up'));
 }finally{storagePrototype.setItem=originalSet;await act(async()=>root.unmount());}
});

test('walls, doors, columns and resize handles drag with undo and Escape recovery',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));const original=saved();
 const canvas=()=>document.querySelector('.plan-canvas');
 const drag=async(label,dx,dy)=>{await event(document.querySelector(`[aria-label="${label}"]`),'pointerdown',{clientX:100,clientY:100});await event(canvas(),'pointermove',{clientX:100+dx,clientY:100-dy});await event(canvas(),'pointerup');};
 await drag('Move wall 3',0,304.8);assert.equal(saved().room.depth,original.room.depth+304.8);
 await event(button('Undo'),'click');assert.deepEqual(saved(),original);
 await drag('Move corner 3',304.8,304.8);assert.equal(saved().room.width,original.room.width+304.8);
 await event(button('Undo'),'click');assert.deepEqual(saved(),original);
 await event(document.querySelector('.equipment-shape'),'pointerdown',{clientX:100,clientY:100});await event(canvas(),'pointerup');
 await drag('Resize SWBD-1 corner 4',304.8,152.4);assert.equal(saved().equipment[0].width,original.equipment[0].width+304.8);
 await event(button('Undo'),'click');assert.deepEqual(saved(),original);
 const obstacle=[...document.querySelectorAll('g')].find(g=>g.textContent==='COLUMN-1');
 await event(obstacle,'pointerdown',{clientX:100,clientY:100});await event(canvas(),'pointermove',{clientX:150,clientY:50});await event(canvas(),'pointerup');
 assert.equal(saved().room.obstacles[0].x,original.room.obstacles[0].x+50.8);
 await event(button('Undo'),'click');assert.deepEqual(saved(),original);
 await event(document.querySelector('[aria-label="Move wall 3"]'),'pointerdown',{clientX:100,clientY:100});await event(canvas(),'pointermove',{clientX:100,clientY:-200});
 await act(async()=>window.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape',bubbles:true})));
 await event(canvas(),'lostpointercapture');assert.deepEqual(saved(),original);
 // Dragging a wall past the opposite side is rejected without an undo entry.
 await drag('Move wall 3',0,-7000);assert.deepEqual(saved(),original);assert.ok(document.body.textContent.includes('drag was undone'));
 }finally{await act(async()=>root.unmount());}
});

test('repeated wall pointer events keep the view steady and do not compound movement',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));const original=saved(),canvas=document.querySelector('.plan-canvas'),viewBox=canvas.getAttribute('viewBox');
 await event(document.querySelector('[aria-label="Move wall 3"]'),'pointerdown',{clientX:100,clientY:100});
 for(let n=0;n<3;n++)await event(canvas,'pointermove',{clientX:100,clientY:-204.8});
 assert.equal(canvas.getAttribute('viewBox'),viewBox,'camera must remain fixed during wall drag');
 assert.equal(document.querySelector('.corner-handle').parentElement.getAttribute('transform'),`translate(0 ${original.room.depth}) scale(1 -1)`);
 await event(canvas,'pointerup');assert.equal(saved().room.depth,original.room.depth+304.8);
 await event(button('Undo'),'click');assert.deepEqual(saved(),original);
 }finally{await act(async()=>root.unmount());}
});


test('empty canvas can become a custom outline or either optional preset, and undo returns to empty',async()=>{
 const {root}=setup();try{
 await act(async()=>root.render(React.createElement(App)));
 await event(button('New blank project'),'click');
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Start blank project'),'click');
 assert.equal(saved().room.defined,false);assert.equal(document.querySelector('.room-boundary'),null);
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Draw my room'),'click');
 assert.equal(document.querySelector('.empty-room-choices'),null);
 const canvas=document.querySelector('.plan-canvas');
 const points=[[508,508],[3556,508],[3556,2540],[2032,2540],[2032,3556],[508,3556]];
 for(const [x,y] of points)await event(canvas,'pointerdown',{clientX:x,clientY:4876.8-y});
 assert.equal(document.querySelectorAll('.draft-outline circle').length,6);
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Finish polygon'),'click');
 assert.equal(saved().room.defined,true);assert.equal(saved().room.width,3048);assert.equal(saved().room.depth,3048);
 assert.deepEqual(saved().room.boundary,[[0,0],[3048,0],[3048,2032],[1524,2032],[1524,3048],[0,3048]]);
 assert.ok(document.querySelector('.room-boundary'));await event(button('Undo'),'click');
 assert.equal(saved().room.defined,false);assert.equal(document.querySelector('.room-boundary'),null);
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Rectangle'),'click');
 assert.equal(saved().room.defined,true);assert.equal(saved().room.notch,0);assert.ok(document.querySelector('.room-boundary'));
 await event(button('Undo'),'click');
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='L-shaped room'),'click');
 assert.equal(saved().room.defined,true);assert.ok(saved().room.notch>0);
 await event(button('Undo'),'click');
 await event([...document.querySelectorAll('button')].find(b=>b.textContent==='Draw my room'),'click');
 await event(canvas,'pointerdown',{clientX:508,clientY:508});
 await act(async()=>window.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape',bubbles:true})));
 assert.equal(saved().room.defined,false);assert.equal(document.querySelector('.room-boundary'),null);assert.ok(document.querySelector('.empty-room-choices'));
 }finally{await act(async()=>root.unmount());}
});
