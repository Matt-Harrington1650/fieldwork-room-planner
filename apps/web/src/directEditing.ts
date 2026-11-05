import {roomPoints,footprint,type Project,type Point,type Item,type Door} from './domain.ts';
import {signedArea,pointInside} from './planner.ts';

const EPS=.01;
const sub=(a:Point,b:Point):Point=>[a[0]-b[0],a[1]-b[1]];
const dot=(a:Point,b:Point)=>a[0]*b[0]+a[1]*b[1];
const cross=(a:Point,b:Point)=>a[0]*b[1]-a[1]*b[0];
const clamp=(v:number,a:number,b:number)=>Math.max(a,Math.min(b,v));
export function edges(p:Project){const ps=roomPoints(p);return ps.map((a,i)=>{const b=ps[(i+1)%ps.length],v=sub(b,a),length=Math.hypot(...v);return {a,b,length,dir:[v[0]/length,v[1]/length] as Point};});}
export function nearestWall(p:Project,pt:Point,minLength=0){return edges(p).map((e,index)=>{const t=clamp(dot(sub(pt,e.a),e.dir),0,e.length),point=[e.a[0]+e.dir[0]*t,e.a[1]+e.dir[1]*t] as Point;return {...e,index,t,point,distance:Math.hypot(...sub(pt,point))};}).filter(e=>e.length>=minLength).sort((a,b)=>a.distance-b.distance)[0];}
function onSegment(p:Point,a:Point,b:Point){return Math.abs(cross(sub(p,a),sub(b,a)))<EPS&&dot(sub(p,a),sub(p,b))<=EPS;}
function intersects(a:Point,b:Point,c:Point,d:Point){const ab=sub(b,a),cd=sub(d,c),x=cross(ab,sub(c,a)),y=cross(ab,sub(d,a)),u=cross(cd,sub(a,c)),v=cross(cd,sub(b,c));return x*y<0&&u*v<0||onSegment(c,a,b)||onSegment(d,a,b)||onSegment(a,c,d)||onSegment(b,c,d);}
export function validOutline(ps:Point[]){if(ps.length<3||ps.length>200||ps.some(p=>p.some(v=>!Number.isFinite(v)||Math.abs(v)>100000))||Math.abs(signedArea(ps))<610*610)return false;
 for(let i=0;i<ps.length;i++){const a=ps[i],b=ps[(i+1)%ps.length];if(Math.hypot(...sub(b,a))<76.2)return false;for(let j=i+1;j<ps.length;j++){if(j===i+1||i===0&&j===ps.length-1)continue;if(intersects(a,b,ps[j],ps[(j+1)%ps.length]))return false;}}
 return true;
}
export function defineRoom(p:Project,points:Point[]):Project{
 if(!validOutline(points))throw Error('Draw a non-crossing outline with walls at least 3 in. long and area at least 4 ft².');
 const minX=Math.min(...points.map(pt=>pt[0])),minY=Math.min(...points.map(pt=>pt[1])),width=Math.max(...points.map(pt=>pt[0]))-minX,depth=Math.max(...points.map(pt=>pt[1]))-minY;
 if(width<610||depth<610||width>50000||depth>50000)throw Error('Room width and depth must be between 2 ft and 164 ft.');
 const shift=(pt:Point):Point=>[pt[0]-minX,pt[1]-minY];
 return {...p,room:{...p.room,defined:true,width,depth,notch:0,boundary:points.map(shift),holes:p.room.holes?.map(ps=>ps.map(shift)),doors:p.room.doors?.map(d=>({...d,x:d.x-minX,y:d.y-minY})),obstacles:p.room.obstacles?.map(o=>({...o,x:o.x-minX,y:o.y-minY}))},equipment:p.equipment.map(e=>({...e,x:e.x-minX,y:e.y-minY})),regions:p.regions?.map(r=>({...r,x:r.x-minX,y:r.y-minY})),underlay:p.underlay?{...p.underlay,x:p.underlay.x-minX,y:p.underlay.y-minY}:undefined};
}
export function doorOnWall(p:Project,d:Door,pt:Point,step:number):Door{const e=nearestWall(p,pt,d.width);if(!e)return d;const t=clamp(Math.round(e.t/step)*step,0,e.length-d.width);return {...d,x:e.a[0]+e.dir[0]*t,y:e.a[1]+e.dir[1]*t,angle:Math.atan2(e.dir[1],e.dir[0])*180/Math.PI};}
function rearCenter(e:Item):Point{const r=footprint(e);return e.rotation===0?[r.x+r.w/2,r.y]:e.rotation===90?[r.x+r.w,r.y+r.h/2]:e.rotation===180?[r.x+r.w/2,r.y+r.h]:[r.x,r.y+r.h/2];}

// A room edit is calculated from its original snapshot on every pointer move.
// Attachments use the original edge and absolute distance from its start.
export function reshapeRoom(p:Project,points:Point[],edgeMap?:number[]):Project{
 if(!validOutline(points)||signedArea(points)*signedArea(roomPoints(p))<=0)throw Error('Walls cannot cross, collapse, or form a room smaller than 4 ft².');
 const old=edges(p),next={...p,room:{...p.room,boundary:points,notch:0}},newEdges=edges(next);
 const mapped=(i:number)=>newEdges[edgeMap?.[i]??i];
 const attachmentMove=(pt:Point,i:number,halfWidth=0):Point=>{const a=old[i],b=mapped(i);if(!b||b.length<halfWidth*2)throw Error('That wall is too short for its attached equipment or door.');const t=clamp(dot(sub(pt,a.a),a.dir),halfWidth,b.length-halfWidth);return [b.a[0]+b.dir[0]*t-pt[0],b.a[1]+b.dir[1]*t-pt[1]];};
 const attachmentDeltas=new Map<string,Point>();
 let equipment=p.equipment.map(e=>{const back=rearCenter(e),wall=nearestWall(p,back);if(!wall||e.wall==='any'&&Math.abs(wall.distance-(e.rear??0))>25.4)return e;
  const normal:Point=e.rotation===0?[0,1]:e.rotation===90?[-1,0]:e.rotation===180?[0,-1]:[1,0];
  const inward:Point=signedArea(roomPoints(p))>0?[-wall.dir[1],wall.dir[0]]:[wall.dir[1],-wall.dir[0]];
  if(dot(normal,inward)<.999)return e;
  const delta=attachmentMove(wall.point,wall.index,e.width/2);
  attachmentDeltas.set(e.id,delta);
  if(e.locked&&Math.hypot(...delta)>EPS)throw Error('Unlock '+e.id+' before moving its supporting wall.');
  return {...e,x:e.x+delta[0],y:e.y+delta[1]};});
 for(const group of new Set(p.equipment.map(e=>e.group).filter(Boolean))){const members=p.equipment.filter(e=>e.group===group),deltas=members.flatMap(e=>attachmentDeltas.has(e.id)?[attachmentDeltas.get(e.id)!]:[]);if(!deltas.length)continue;const delta=deltas[0];if(deltas.some(d=>Math.hypot(d[0]-delta[0],d[1]-delta[1])>EPS))throw Error('This assembly is attached to walls moving in different directions. Release the assembly before reshaping.');if(members.some(e=>e.locked)&&Math.hypot(...delta)>EPS)throw Error('Unlock the complete assembly before moving its supporting wall.');equipment=equipment.map(e=>{const original=members.find(m=>m.id===e.id);return original?{...e,x:original.x+delta[0],y:original.y+delta[1]}:e;});}
 const doors=p.room.doors?.map(d=>{const wall=nearestWall(p,[d.x,d.y]);if(!wall||wall.distance>25.4)return d;const b=mapped(wall.index);if(b.length<d.width)throw Error('That wall is too short for its door.');const t=clamp(wall.t,0,b.length-d.width);return {...d,x:b.a[0]+b.dir[0]*t,y:b.a[1]+b.dir[1]*t,angle:Math.atan2(b.dir[1],b.dir[0])*180/Math.PI};});
 // Keep the lower-left origin at zero, translating all objects consistently.
 const minX=Math.min(...points.map(pt=>pt[0])),minY=Math.min(...points.map(pt=>pt[1])),shift=(pt:Point):Point=>[pt[0]-minX,pt[1]-minY];
 const width=Math.max(...points.map(pt=>pt[0]))-minX,depth=Math.max(...points.map(pt=>pt[1]))-minY;
 if(width<610||depth<610||width>50000||depth>50000)throw Error('Room width and depth must be between 2 ft and 164 ft.');
 const holes=p.room.holes??[];
 for(const hole of holes){if(hole.some(pt=>!pointInside(pt,points))||hole.some((a,i)=>points.some((b,j)=>intersects(a,hole[(i+1)%hole.length],b,points[(j+1)%points.length]))))throw Error('The room wall cannot cross an existing room hole.');}
 return {...next,equipment:equipment.map(e=>({...e,x:e.x-minX,y:e.y-minY})),room:{...next.room,width,depth,boundary:points.map(shift),holes:holes.map(ps=>ps.map(shift)),doors:doors?.map(d=>({...d,x:d.x-minX,y:d.y-minY})),obstacles:p.room.obstacles?.map(o=>({...o,x:o.x-minX,y:o.y-minY}))},regions:p.regions?.map(r=>({...r,x:r.x-minX,y:r.y-minY})),underlay:p.underlay?{...p.underlay,x:p.underlay.x-minX,y:p.underlay.y-minY}:undefined};
}
export function dragWall(p:Project,index:number,dx:number,dy:number):Project{
 const ps=roomPoints(p),es=edges(p),e=es[index],normal:Point=[-e.dir[1],e.dir[0]],distance=dx*normal[0]+dy*normal[1],delta:Point=[normal[0]*distance,normal[1]*distance],next:Point[]=[],mapping:number[]=[];
 // Collinear split segments get short return walls so dragging creates a jog.
 for(let i=0;i<ps.length;i++){const prev=(i+ps.length-1)%ps.length,isStart=i===index,isEnd=i===(index+1)%ps.length;
  if(isStart&&Math.abs(cross(es[prev].dir,e.dir))<EPS)next.push([...ps[i]]);
  if(isEnd&&Math.abs(cross(e.dir,es[i].dir))<EPS){next.push([ps[i][0]+delta[0],ps[i][1]+delta[1]]);}
  mapping[i]=next.length;
  next.push(isStart||isEnd?[ps[i][0]+delta[0],ps[i][1]+delta[1]]:[...ps[i]]);
  if(isEnd&&Math.abs(cross(e.dir,es[i].dir))<EPS)next[next.length-1]=[...ps[i]];
 }
 if(Math.abs(distance)<EPS)return p;
 return reshapeRoom(p,next,mapping);
}
export function dragCorner(p:Project,index:number,dx:number,dy:number):Project{
 if(Math.hypot(dx,dy)<EPS)return p;
 const ps=roomPoints(p).map(pt=>[...pt] as Point),n=ps.length,prev=(index+n-1)%n,next=(index+1)%n,at=ps[index],before=[...at] as Point;
 ps[index]=[at[0]+dx,at[1]+dy];
 if(Math.abs(ps[prev][0]-before[0])<EPS)ps[prev][0]+=dx;else if(Math.abs(ps[prev][1]-before[1])<EPS)ps[prev][1]+=dy;
 if(Math.abs(ps[next][0]-before[0])<EPS)ps[next][0]+=dx;else if(Math.abs(ps[next][1]-before[1])<EPS)ps[next][1]+=dy;
 return reshapeRoom(p,ps);
}
export function setWallLength(p:Project,index:number,length:number):Project{const e=edges(p)[index];return dragCorner(p,(index+1)%roomPoints(p).length,e.dir[0]*(length-e.length),e.dir[1]*(length-e.length));}
export function splitWall(p:Project,index:number):Project{const ps=roomPoints(p).map(pt=>[...pt] as Point),a=ps[index],b=ps[(index+1)%ps.length];if(Math.hypot(...sub(b,a))<152.4)throw Error('A wall must be at least 6 in. long to split.');ps.splice(index+1,0,[(a[0]+b[0])/2,(a[1]+b[1])/2]);return {...p,room:{...p.room,boundary:ps,notch:0}};}
export function resizeItem(e:Item,corner:number,dx:number,dy:number):Item{if(e.locked||e.group)return e;const r=footprint(e),west=corner===0||corner===2,south=corner<2,w=clamp(r.w+(west?-dx:dx),25.4,20000),h=clamp(r.h+(south?-dy:dy),25.4,20000);return {...e,x:west?r.x+r.w-w:r.x,y:south?r.y+r.h-h:r.y,width:e.rotation%180===0?w:h,depth:e.rotation%180===0?h:w};}
