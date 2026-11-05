"""Bounded offline reference imports. Never executes embedded CAD content."""
import io,base64,math
import ezdxf
from shapely.geometry import Polygon

def import_dxf(text):
    if len(text)>10_000_000:raise ValueError('DXF size limit is 10 MB.')
    doc=ezdxf.read(io.StringIO(text));space=doc.modelspace()
    if len(space)>25000:raise ValueError('DXF exceeds 25,000 modelspace entities.')
    units=doc.units;factor={1:25.4,2:304.8,4:1,5:10,6:1000}.get(units)
    if factor is None:raise ValueError('DXF needs explicit supported drawing units (inches, feet, millimeters, centimeters, or meters).')
    polygons=[]
    for e in space:
        if e.dxftype()=='LWPOLYLINE' and e.closed:
            if any(abs(v[4])>1e-9 for v in e.get_points()):continue
            pts=[(float(v[0])*factor,float(v[1])*factor) for v in e.get_points()]
            if len(pts)>200:continue
            poly=Polygon(pts)
            if poly.is_valid and poly.area>0:polygons.append(poly)
    if not polygons:raise ValueError('No closed, straight-segment room polyline found. Export the room as a closed LWPOLYLINE.')
    room=max(polygons,key=lambda g:g.area);minx,miny,maxx,maxy=room.bounds
    if maxx-minx>50000 or maxy-miny>50000:raise ValueError('Room exceeds supported 164-foot extents.')
    points=[(x-minx,y-miny) for x,y in list(room.exterior.coords)[:-1]]
    holes=[];obs=[]
    for index,poly in enumerate(polygons):
        if poly is room or not room.contains(poly):continue
        x,y,mx,my=poly.bounds;obs.append({'id':f'DXF-OBS-{index}','kind':'imported obstruction','x':x-minx,'y':y-miny,'width':mx-x,'depth':my-y,'bottom':0,'top':3048})
    return {'room':{'width':maxx-minx,'depth':maxy-miny,'boundary':points,'notch':0,'holes':holes,'doors':[],'obstacles':obs,'column':False},'notice':'Largest valid closed polyline imported as room. Interior polylines become conservative bounding-box obstructions. Add and verify doors; text, arcs, bulges, blocks and open lines are not traced automatically.'}

def import_underlay(data):
    encoded=data.split(',',1)[-1]
    if len(encoded)>22_000_000:raise ValueError('PDF reference is too large.')
    raw=base64.b64decode(encoded,validate=True)
    import pypdfium2 as pdfium
    pdf=pdfium.PdfDocument(raw)
    if len(pdf)==0:raise ValueError('PDF has no pages.')
    page=pdf[0];scale=min(2,1800/max(page.get_size()));image=page.render(scale=scale).to_pil();output=io.BytesIO();image.convert('RGB').save(output,format='JPEG',quality=85);page.close();pdf.close()
    return {'data':'data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode(),'notice':'First PDF page rendered. Calibrate and verify before tracing.'}
