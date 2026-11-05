"""Conservative rigid rectangular load study with exact straight sweeps and full-circle turns."""
from collections import deque
import math,time
from shapely.geometry import box,Point,Polygon
from shapely.ops import unary_union
from .geometry import room_polygon,footprint

def study(p,equipment_id,width,depth,allowance=0,time_limit=3):
    item=next((e for e in p.equipment if e.id==equipment_id),None)
    if item is None:raise ValueError('Select existing equipment.')
    width=max(1,width+allowance*2);depth=max(1,depth+allowance*2)
    if max(width,depth)>20000:raise ValueError('Replacement load exceeds supported dimensions.')
    room=room_polygon(p);openings=[];extension=math.hypot(width,depth)+610
    for d in p.room.doors or []:
        if not d.egress or abs(d.angle%90)>.001:continue
        a=math.radians(d.angle);u=(math.cos(a),math.sin(a));n=(-u[1],u[0])
        points=[(d.x+u[0]*t+n[0]*s,d.y+u[1]*t+n[1]*s) for t,s in [(0,-extension),(d.width,-extension),(d.width,extension),(0,extension)]]
        openings.append(Polygon(points))
    if not openings:return {'status':'UNRESOLVED','path':[],'message':'No orthogonal designated door is defined. Add and verify an access opening.'}
    blocked=[footprint(e) for e in p.equipment if e.id!=item.id and e.bottom<item.bottom+item.height and e.bottom+e.height>item.bottom]
    blocked += [box(o.x,o.y,o.x+o.width,o.y+o.depth) for o in p.room.obstacles or [] if o.bottom<item.bottom+item.height and o.top>item.bottom]
    free=unary_union([room,*openings]).difference(unary_union(blocked))
    start_center=footprint(item).centroid;cx,cy=start_center.x,start_center.y;step=152.4;start=(0,0,item.rotation//90%2);queue=deque([start]);parent={start:None};cache={};deadline=time.monotonic()+time_limit
    def shape(state):
        ix,iy,r=state;w,h=(width,depth) if r==0 else (depth,width);x,y=cx+ix*step,cy+iy*step
        return box(x-w/2,y-h/2,x+w/2,y+h/2)
    def legal(state):
        if state not in cache:cache[state]=free.buffer(.001).covers(shape(state))
        return cache[state]
    if not legal(start):return {'status':'UNRESOLVED','path':[],'message':'The defined replacement load and handling allowance do not fit at the starting position.'}
    goal=None
    while queue and len(parent)<20000 and time.monotonic()<deadline:
        state=queue.popleft();poly=shape(state)
        if not poly.intersects(room):goal=state;break
        x,y,r=state
        for next_state in [(x+1,y,r),(x-1,y,r),(x,y+1,r),(x,y-1,r),(x,y,1-r)]:
            if next_state in parent or not legal(next_state):continue
            if next_state[2]!=r:
                # Circumscribed disk contains every orientation, avoiding angular sampling gaps.
                radius=math.hypot(width,depth)/2/math.cos(math.pi/64)
                swept=Point(cx+x*step,cy+y*step).buffer(radius,quad_segs=16)
            else:swept=unary_union([poly,shape(next_state)]).convex_hull
            if not free.buffer(.001).covers(swept):continue
            parent[next_state]=state;queue.append(next_state)
    if goal is None:return {'status':'UNRESOLVED','path':[],'states':len(parent),'message':'No conservative rigid-load route found on the 6-inch grid within the time budget. This does not prove that no continuous path exists.'}
    route=[]
    while goal is not None:
        route.append({'x':cx+goal[0]*step,'y':cy+goal[1]*step,'rotation':goal[2]*90});goal=parent[goal]
    return {'status':'PASSED_IMPLEMENTED_STUDY','path':list(reversed(route)),'states':len(parent),'message':'A conservative planar route was found for the entered rectangular load and handling allowance. Straight moves check the full swept shape; turns require full-circle clearance. Verify door operation, overhead path, handling equipment, and site conditions separately.'}
