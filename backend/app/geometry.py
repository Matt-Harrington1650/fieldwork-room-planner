"""Independent exact Cartesian geometry; +Y up; epsilon in square millimeters."""
import math
from shapely.geometry import Polygon, box
from .models import Equipment, Project

AREA_EPSILON = 0.01

def room_points(p: Project):
    if not p.room.defined:return []
    if p.room.boundary:return p.room.boundary
    w,h,n=p.room.width,p.room.depth,p.room.notch
    return [(0,0),(w,0),(w,h-n),(w-n,h-n),(w-n,h),(0,h)] if n else [(0,0),(w,0),(w,h),(0,h)]

def room_polygon(p):
    return Polygon(room_points(p),p.room.holes)

def dimensions(e: Equipment):
    return (e.width,e.depth) if e.rotation % 180 == 0 else (e.depth,e.width)

def footprint(e):
    w,h=dimensions(e)
    return box(e.x,e.y,e.x+w,e.y+h)

def working_zone(e):
    w,h=dimensions(e)
    s=max(e.width,762); o=(s-e.width)/2; d=e.working; x,y=e.x,e.y
    bounds={0:(x-o,y+h,x-o+s,y+h+d),90:(x-d,y-o,x,y-o+s),180:(x-o,y-d,x-o+s,y),270:(x+w,y-o,x+w+d,y-o+s)}
    return box(*bounds[e.rotation])

def rear_zone(e):
    if not e.rear:
        return None
    w,h=dimensions(e); x,y=e.x,e.y; d=e.rear
    bounds={0:(x,y-d,x+w,y),90:(x+w,y,x+w+d,y+h),180:(x,y+h,x+w,y+h+d),270:(x-d,y,x,y+h)}
    return box(*bounds[e.rotation])

def door_sweep(d):
    angle=math.radians(d.angle)
    return Polygon([(d.x,d.y)]+[(d.x+math.cos(angle+math.radians(d.sweep)*i/96)*d.width,d.y+math.sin(angle+math.radians(d.sweep)*i/96)*d.width) for i in range(97)])

def obstacles(p,e=None):
    result=[]
    if p.room.obstacles is not None:
        result.extend((o.id,box(o.x,o.y,o.x+o.width,o.y+o.depth)) for o in p.room.obstacles if e is None or (o.bottom<e.bottom+max(e.height,1981.2) and o.top>e.bottom))
    elif p.room.column:
        result.append(('COLUMN-1',box(3550,2600,4000,3050)))
    # Door hinge at 3300,0, closed along +X, opening 90 degrees inward.
    # Circumscribed wedge is conservatively larger than the true sweep.
    if p.room.doors is not None:result.extend((d.id,door_sweep(d)) for d in p.room.doors if abs(d.sweep)>0)
    else:
        r=p.room.door
        result.append(('DOOR-1',box(3300,0,3300+r,r)))
    result.extend((r.id,box(r.x,r.y,r.x+r.width,r.y+r.depth)) for r in p.regions if r.hard and r.kind in ['forbidden','future'])
    return result

def side_zone(e,side,distance):
    if side in ['top','bottom']:return footprint(e)
    w,h=dimensions(e);x,y=e.x,e.y;index=(['front','left','rear','right'].index(side)+e.rotation//90)%4
    return box(*[(x,y+h,x+w,y+h+distance),(x-distance,y,x,y+h),(x,y-distance,x+w,y),(x+w,y,x+w+distance,y+h)][index])

def extra_zones(e,hard_only=True):
    result=[(z,side_zone(e,z.side,z.distance)) for z in e.zones if z.distance>0 and (not hard_only or z.hard)]
    if e.panelSwing:
        # Local front hinge transformed with the equipment orientation.
        w,h=dimensions(e)
        from .models import Door
        x,y,a={0:(e.x,e.y+h,0),90:(e.x,e.y,-90),180:(e.x+w,e.y,180),270:(e.x+w,e.y+h,90)}[e.rotation]
        result.append((None,door_sweep(Door(id=e.id+'-panel',x=x,y=y,width=e.width,angle=a,sweep=e.panelSwing))))
    return result

def height_overlap(a,b):return a.bottom<b.bottom+b.height and b.bottom<a.bottom+a.height

def overlap(a,b):
    return a.intersection(b).area > AREA_EPSILON

def valid_static(p,e):
    room=room_polygon(p)
    zones=[footprint(e),working_zone(e)]
    if rear_zone(e) is not None: zones.append(rear_zone(e))
    if e.bottom+e.height>p.room.height:return False
    if not all(room.buffer(.001).covers(z) and not any(overlap(z,o) for _,o in obstacles(p,e)) for z in zones):return False
    for record,poly in extra_zones(e):
        low,high=zone_elevation(e,record)
        if high>p.room.height or low<0:return False
        probe=e.model_copy(update={'bottom':low,'height':high-low})
        if not room.buffer(.001).covers(poly) or any(overlap(poly,o) for _,o in obstacles(p,probe)):return False
    return True

def zone_elevation(e,record):
    if record and record.side=='top':return e.bottom+e.height,e.bottom+e.height+record.distance
    if record and record.side=='bottom':return e.bottom-record.distance,e.bottom
    return (e.bottom+(record.bottom if record else 0),e.bottom+(record.top if record else e.height))

def incompatible(a,b):
    fa,fb=footprint(a),footprint(b)
    return (overlap(fa,fb) or overlap(working_zone(a),fb) or overlap(working_zone(b),fa)
            or (rear_zone(a) is not None and overlap(rear_zone(a),fb))
            or (rear_zone(b) is not None and overlap(rear_zone(b),fa)))
