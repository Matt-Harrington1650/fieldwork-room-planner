import {formatLength} from './imperial.ts';
export type Point = [number,number];
export type Door={id:string;x:number;y:number;width:number;angle:number;sweep:number;egress:boolean};
export type Obstacle={id:string;kind:string;x:number;y:number;width:number;depth:number;bottom:number;top:number};
export type Zone={id:string;kind:'service'|'ventilation'|'removal'|'future'|'buffer';side:'front'|'rear'|'left'|'right'|'top'|'bottom';distance:number;hard:boolean;source:string;bottom:number;top:number};
export type Item = {id:string;category:string;name:string;x:number;y:number;width:number;depth:number;rotation:number;locked:boolean;working:number;rear:number|null;voltage:number;condition:number;status:string;wall:string;height?:number;bottom?:number;zones?:Zone[];group?:string;definition?:string;source?:string;manufacturer?:string;model?:string;panelSwing?:number;};
export type Room={defined?:boolean;width:number;depth:number;notch:number;door:number;column:boolean;boundary?:Point[];holes?:Point[][];doors?:Door[];obstacles?:Obstacle[];height?:number;access_width?:number;check_access?:boolean};
export type Underlay={name:string;data:string;x:number;y:number;width:number;height:number;opacity:number;locked:boolean;rotation:number;calibrated:boolean};
export type Scenario={id:string;name:string;created:string;equipment:Item[];room:Room;notes:string;};
export type Definition={id:string;version:number;name:string;item:Item;favorite:boolean};
export type Region={id:string;name:string;x:number;y:number;width:number;depth:number;kind:'forbidden'|'future'|'required';hard:boolean};
export type Project = {schema_version:string;name:string;units:'mm'|'ft';room:Room;equipment:Item[];underlay?:Underlay;scenarios?:Scenario[];definitions?:Definition[];regions?:Region[];notes?:string;jurisdiction?:string;ruleEdition?:string;};
export type Finding = {rule_id:string;status:string;severity:string;equipment_ids:string[];message:string;required?:unknown;actual?:unknown;};
export type Alternative = {id:string;score:number;equipment:Item[];diagnostics:Finding[]};
export function parseProject(text:string):Project{
 const p=JSON.parse(text);const finite=(n:unknown,min:number,max:number)=>typeof n==='number'&&Number.isFinite(n)&&n>=min&&n<=max;
 if(!p||p.schema_version!=='1.0.0'||typeof p.name!=='string'||p.name.length>200||!['mm','ft'].includes(p.units)||!p.room||!Array.isArray(p.equipment)||p.equipment.length>100)throw Error('Invalid version 1.0.0 project.');
 const r=p.room;
 if(r.defined!==undefined&&typeof r.defined!=='boolean')throw Error('Invalid room state.');
 if(!finite(r.width,610,50000)||!finite(r.depth,610,50000)||!finite(r.notch,0,10000)||r.notch>=Math.min(r.width,r.depth)||!finite(r.door,600,2000)||typeof r.column!=='boolean')throw Error('Invalid room dimensions.');
 if(r.doors===undefined&&r.width<3300+r.door)throw Error('Legacy door opening is outside the room.');
 const points=(ps:unknown)=>Array.isArray(ps)&&ps.length>=3&&ps.length<=200&&ps.every(pt=>Array.isArray(pt)&&pt.length===2&&pt.every(n=>finite(n,-100000,100000)));
 if(r.boundary!==undefined&&!points(r.boundary))throw Error('Invalid room boundary.');
 if(r.holes!==undefined&&(!Array.isArray(r.holes)||r.holes.length>50||!r.holes.every(points)))throw Error('Invalid room holes.');
 if(r.doors!==undefined&&(!Array.isArray(r.doors)||r.doors.length>50||!r.doors.every((d:any)=>typeof d.id==='string'&&finite(d.x,-100000,100000)&&finite(d.y,-100000,100000)&&finite(d.width,1,10000)&&finite(d.angle,-360,360)&&finite(d.sweep,-180,180))))throw Error('Invalid doors.');
 if(r.obstacles!==undefined&&(!Array.isArray(r.obstacles)||r.obstacles.length>100||!r.obstacles.every((o:any)=>typeof o.id==='string'&&['x','y','width','depth','bottom','top'].every(k=>finite(o[k],-100000,100000))&&o.width>0&&o.depth>0&&o.top>o.bottom)))throw Error('Invalid obstructions.');
 const ids=new Set();
 for(const e of p.equipment){
 if(!e||typeof e.id!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(e.id)||ids.has(e.id)||typeof e.name!=='string'||e.name.length>200||!['switchboard','switchgear','panelboard','transformer','ats','ups','disconnect','custom'].includes(e.category)||!finite(e.x,-100000,100000)||!finite(e.y,-100000,100000)||!finite(e.width,1,20000)||!finite(e.depth,1,20000)||![0,90,180,270].includes(e.rotation)||typeof e.locked!=='boolean'||!finite(e.working,0,10000)||(e.rear!==null&&!finite(e.rear,0,10000))||!finite(e.voltage,0,100000)||![1,2,3].includes(e.condition)||!['generic','user_entered','verified','unknown'].includes(e.status)||!['any','north','east','south','west'].includes(e.wall))throw Error('Invalid equipment record or duplicate equipment ID.');ids.add(e.id);
 }
 if(p.scenarios!==undefined&&(!Array.isArray(p.scenarios)||p.scenarios.length>50))throw Error('Invalid scenarios.');
 if(p.definitions!==undefined&&(!Array.isArray(p.definitions)||p.definitions.length>200))throw Error('Invalid equipment library.');
 if(p.regions!==undefined&&(!Array.isArray(p.regions)||p.regions.length>100))throw Error('Invalid reservation regions.');
 return p as Project;
}
export const library = [
 {category:'switchboard',name:'Main switchboard',prefix:'SWBD',width:1800,depth:800,working:1200,voltage:277},
 {category:'panelboard',name:'Panelboard',prefix:'PP',width:650,depth:250,working:1000,voltage:120},
 {category:'transformer',name:'Dry-type transformer',prefix:'XFMR',width:1100,depth:850,working:1200,voltage:277},
 {category:'ats',name:'Automatic transfer switch',prefix:'ATS',width:800,depth:500,working:1200,voltage:277},
 {category:'ups',name:'Uninterruptible power supply',prefix:'UPS',width:800,depth:900,working:1200,voltage:277},
 {category:'disconnect',name:'Disconnect switch',prefix:'DS',width:500,depth:250,working:1000,voltage:277},
];
export const seed:Project={schema_version:'1.0.0',name:'North Tower · Electrical E-201',units:'ft',room:{width:8000,depth:6000,notch:0,door:1100,column:true},equipment:[
 {...library[0],id:'SWBD-1',x:600,y:5100,rotation:180,locked:false,rear:null,condition:2,status:'generic',wall:'north'},
 {...library[3],id:'ATS-1',x:2900,y:5400,rotation:180,locked:false,rear:null,condition:2,status:'generic',wall:'north'},
 {...library[1],id:'PP-1',x:4500,y:5650,rotation:180,locked:false,rear:null,condition:1,status:'generic',wall:'north'},
 {...library[1],id:'PP-2',x:5500,y:5650,rotation:180,locked:false,rear:null,condition:1,status:'generic',wall:'north'},
 {...library[2],id:'XFMR-1',x:6800,y:1600,rotation:90,locked:false,rear:null,condition:2,status:'generic',wall:'east'},
]};
export function dimensions(e:Item):Point{return e.rotation%180===0?[e.width,e.depth]:[e.depth,e.width];}
export function footprint(e:Item){const [w,h]=dimensions(e);return {x:e.x,y:e.y,w,h};}
export function workingZone(e:Item){const {x,y,w,h}=footprint(e),s=Math.max(e.width,762),offset=(s-e.width)/2,d=e.working;switch(e.rotation){case 90:return{x:x-d,y:y-offset,w:d,h:s};case 180:return{x:x-offset,y:y-d,w:s,h:d};case 270:return{x:x+w,y:y-offset,w:d,h:s};default:return{x:x-offset,y:y+h,w:s,h:d};}}
export type Rect={x:number;y:number;w:number;h:number};
export function overlaps(a:Rect,b:Rect){return a.x<b.x+b.w-0.01&&a.x+a.w>b.x+0.01&&a.y<b.y+b.h-0.01&&a.y+a.h>b.y+0.01;}
export function roomPoints(p:Project):Point[]{if(p.room.defined===false)return [];if(p.room.boundary?.length)return p.room.boundary;const {width:w,depth:h,notch:n}=p.room;return n?[[0,0],[w,0],[w,h-n],[w-n,h-n],[w-n,h],[0,h]]:[[0,0],[w,0],[w,h],[0,h]];}
export function validateLocal(p:Project):Finding[]{const result:Finding[]=[];const {width:w,depth:h,notch:n}=p.room;const inside=(r:Rect)=>r.x>=-0.01&&r.y>=-0.01&&r.x+r.w<=w+0.01&&r.y+r.h<=h+0.01&&!(n&&overlaps(r,{x:w-n,y:h-n,w:n,h:n}));
const obstacles:Rect[]=[{x:3300,y:0,w:p.room.door,h:p.room.door},...(p.room.column?[{x:3550,y:2600,w:450,h:450}]:[])];
for(const e of p.equipment){const f=footprint(e),z=workingZone(e);const add=(rule_id:string,message:string,severity='error')=>result.push({rule_id,status:severity==='error'?'fail':'unresolved',severity,equipment_ids:[e.id],message});
if(!inside(f))add('GEO-CONTAINMENT','Equipment footprint extends outside the room.');
if(!inside(z))add('SPACE-CONTAINMENT','Working space extends outside the room.');
if(obstacles.some(o=>overlaps(f,o)||overlaps(z,o)))add('GEO-OBSTACLE','Footprint or working space intersects a column or conservative door-sweep envelope.');
for(const other of p.equipment.filter(o=>o.id!==e.id)){if(overlaps(f,footprint(other)))add('GEO-COLLISION',`Equipment footprint overlaps ${other.id}.`);else if(overlaps(z,footprint(other)))add('SPACE-OBSTRUCTION',`Working space is obstructed by ${other.id}.`);}
if(e.rear===null)add('MFR-REAR-UNKNOWN','Rear service requirement is unknown. Verify the manufacturer installation guide.','warning');
const minimum=e.voltage<=150?914:e.voltage<=600?[914,1067,1219][e.condition-1]:null;
if(minimum===null)add('NEC-VOLTAGE-UNSUPPORTED','Voltage exceeds draft rule-pack scope.','warning');
else if(e.working<minimum)add('NEC2023-110.26-A1',`Working depth ${e.working} mm is below draft minimum ${minimum} mm for selected condition ${e.condition}.`);
if(e.rear){const d=e.rear;const r=e.rotation===0?{x:f.x,y:f.y-d,w:f.w,h:d}:e.rotation===180?{x:f.x,y:f.y+f.h,w:f.w,h:d}:e.rotation===90?{x:f.x+f.w,y:f.y,w:d,h:f.h}:{x:f.x-d,y:f.y,w:d,h:f.h};if(!inside(r)||obstacles.some(o=>overlaps(r,o))||p.equipment.some(o=>o.id!==e.id&&overlaps(r,footprint(o))))add('MFR-REAR','Manufacturer rear service clearance is obstructed.');}
if(e.status!=='verified')add('DATA-PROVENANCE','Generic or user-entered dimensions require source review.','warning');}
return result;}
export function svgExport(p:Project){const colors:Record<string,string>={switchboard:'#719b87',panelboard:'#7eabc4',transformer:'#cfaa72',ats:'#a299bb'};return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-400 -400 ${p.room.width+800} ${p.room.depth+800}"><rect x="-400" y="-400" width="${p.room.width+800}" height="${p.room.depth+800}" fill="white"/><g transform="translate(0 ${p.room.depth}) scale(1 -1)"><polygon points="${roomPoints(p).map(x=>x.join(',')).join(' ')}" fill="#fafbf8" stroke="#334a45" stroke-width="40"/>${p.room.column?'<rect x="3550" y="2600" width="450" height="450" fill="#c5ccbd" stroke="#6f7c67" stroke-width="15"/>':''}<path d="M 3300 0 L 3300 ${p.room.door} M 3300 ${p.room.door} A ${p.room.door} ${p.room.door} 0 0 0 ${3300+p.room.door} 0" fill="none" stroke="#6f7c67" stroke-width="15"/>${p.equipment.map(e=>{const f=footprint(e),z=workingZone(e);return `<rect x="${z.x}" y="${z.y}" width="${z.w}" height="${z.h}" fill="#eff7ed" stroke="#78a16a" stroke-dasharray="40 30"/><rect x="${f.x}" y="${f.y}" width="${f.w}" height="${f.h}" fill="${colors[e.category]||'#aaa'}" stroke="#334a45" stroke-width="15"/><text x="${f.x+f.w/2}" y="${-f.y-f.h/2}" transform="scale(1 -1)" font-family="sans-serif" font-size="100" text-anchor="middle">${e.id.replace(/[<>&"']/g,'')}</text>`;}).join('')}</g></svg>`;}
