import io
import re
import ezdxf
from .geometry import room_points,footprint,working_zone,rear_zone,obstacles
from .rules import validate

def imperial_length(mm):
    ticks=round(abs(mm)/25.4*16);feet,rem=divmod(ticks,192);inches,num=divmod(rem,16)
    if num:
        import math
        factor=math.gcd(num,16);fraction=f' {num//factor}/{16//factor}'
    else:fraction=''
    return f'{"-" if mm<0 and ticks else ""}{feet}\' {inches}{fraction}"'

def export_report(p):
    report=validate(p)
    def convert(value):
        if isinstance(value,dict):return {key[:-3]+'_in' if key.endswith('_mm') else key:(round(val/25.4,6) if key.endswith('_mm') and isinstance(val,(int,float)) else convert(val)) for key,val in value.items()}
        if isinstance(value,list):return [convert(v) for v in value]
        if isinstance(value,str):return re.sub(r'(-?\d+(?:\.\d+)?)\s*mm\b',lambda m:imperial_length(float(m[1])),value)
        return value
    return {'project_name':p.name,'units':'imperial','linear_unit':'inches','room':{'width':imperial_length(p.room.width),'depth':imperial_length(p.room.depth),'area_sq_ft':round((p.room.width*p.room.depth-p.room.notch**2)/304.8**2,3)},
            'equipment_schedule':[{'id':e.id,'category':e.category,'x_in':e.x/25.4,'y_in':e.y/25.4,'width_in':e.width/25.4,'depth_in':e.depth/25.4,'front_clearance_in':e.working/25.4,'rear_clearance_in':None if e.rear is None else e.rear/25.4,'rotation_deg':e.rotation} for e in p.equipment],
            'validation':convert(report),'notice':'Draft implemented checks only. Not a universal code compliance determination.'}

def export_dxf(p):
    doc=ezdxf.new('R2018');doc.units=1;space=doc.modelspace()
    for layer,color in [('E-ROOM',7),('E-DOOR',3),('E-OBS',8),('E-EQPM',4),('E-EQPM-TEXT',7),('E-WORK',3),('E-MFR-CLR',6),('E-WARN',1)]:
        doc.layers.new(layer,dxfattribs={'color':color})
    space.add_lwpolyline([(x/25.4,y/25.4) for x,y in room_points(p)],close=True,dxfattribs={'layer':'E-ROOM'})
    for oid,o in obstacles(p):space.add_lwpolyline([(x/25.4,y/25.4) for x,y in list(o.exterior.coords)[:-1]],close=True,dxfattribs={'layer':'E-DOOR' if oid.startswith('DOOR') else 'E-OBS'})
    for e in p.equipment:
        for g,layer in [(footprint(e),'E-EQPM'),(working_zone(e),'E-WORK'),(rear_zone(e),'E-MFR-CLR')]:
            if g is not None:space.add_lwpolyline([(x/25.4,y/25.4) for x,y in list(g.exterior.coords)[:-1]],close=True,dxfattribs={'layer':layer})
        center=footprint(e).centroid
        space.add_text(e.id,dxfattribs={'layer':'E-EQPM-TEXT','height':100/25.4}).set_placement((center.x/25.4,center.y/25.4))
    space.add_text('DRAFT - implemented checks only; engineering review required',dxfattribs={'layer':'E-WARN','height':100/25.4}).set_placement((0,-400/25.4))
    stream=io.StringIO();doc.write(stream);return stream.getvalue()
