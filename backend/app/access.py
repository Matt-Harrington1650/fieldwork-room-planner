"""Conservative planar access-corridor connectivity. Not code-specific egress certification."""
import math
from shapely.geometry import Point,box
from shapely.ops import unary_union
from .geometry import room_polygon,footprint,working_zone

def check_access(p):
    width=p.room.access_width;radius=width/2
    blockers=[footprint(e) for e in p.equipment if e.bottom<1981.2]
    blockers += [box(o.x,o.y,o.x+o.width,o.y+o.depth) for o in p.room.obstacles or [] if o.bottom<1981.2]
    # Square joins deliberately err toward larger exclusions at sharp corners.
    free=room_polygon(p).buffer(-radius,join_style=2).difference(unary_union(blockers).buffer(radius,join_style=2))
    components=list(free.geoms) if free.geom_type=='MultiPolygon' else [free]
    exits=[]
    for d in p.room.doors or []:
        if not d.egress or d.width<width:continue
        a=math.radians(d.angle);cx=d.x+math.cos(a)*d.width/2;cy=d.y+math.sin(a)*d.width/2
        for sign in [-1,1]:
            candidate=Point(cx-sign*math.sin(a)*(radius+1),cy+sign*math.cos(a)*(radius+1))
            if free.buffer(.01).covers(candidate):exits.append(candidate)
    result=[]
    def finding(ids,message,severity='error'):
        result.append({'rule_id':'PROJECT-ACCESS-CONNECTIVITY','status':'fail' if severity=='error' else 'unresolved','severity':severity,'equipment_ids':ids,'message':message,'required':{'width_mm':width},'actual':None,'source':{'standard':'User-defined planar corridor','review_status':'project-specific'}})
    if not exits:finding([],f'No designated door connects to a {width} mm conservative clear corridor. Check door width, location and obstacles.')
    for e in p.equipment:
        zone=working_zone(e)
        reachable=any(c.intersection(zone).area>.01 and any(c.buffer(.01).covers(exit) for exit in exits) for c in components if not c.is_empty)
        if not reachable:finding([e.id],f'Working zone has no connected {width} mm conservative planar access route to a designated door.')
    finding([],'Planar route check uses a user-defined circular clearance footprint. It does not evaluate code-specific egress triggers, headroom along the route, travel distance limits or replacement-load turning.','warning')
    return result
