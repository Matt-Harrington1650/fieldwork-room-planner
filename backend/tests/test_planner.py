import io,base64,threading
import pytest
from pydantic import ValidationError
from app.models import Project,Equipment,Settings,Room,Zone
from app.geometry import room_polygon,valid_static,side_zone,door_sweep,footprint
from app.rules import validate
from app.solver import solve,candidates
from app.deliverables import export_pdf,export_xlsx
from app.importers import import_dxf,import_underlay
from app.exporters import export_dxf

def item(**kw):return Equipment(**{'id':'PP-1','name':'Panel','category':'panelboard','x':1000,'y':0,'width':650,'depth':250,'working':1000,'rear':0,'status':'verified',**kw})
def project(items=None,**room):return Project(name='Planner fixture',room={'width':8000,'depth':6000,'doors':[],'obstacles':[],'column':False,**room},equipment=items if items is not None else [item()])
def errors(p):return [f for f in validate(p)['diagnostics'] if f['severity']=='error']

def test_arbitrary_room_and_hole():
    p=project(boundary=[(0,0),(8000,0),(8000,4000),(5000,6000),(0,6000)],holes=[[(3000,2000),(3500,2000),(3500,2500),(3000,2500)]])
    assert room_polygon(p).is_valid
    assert not valid_static(p,item(x=3100,y=2100))
    assert valid_static(p,item())
def test_bow_tie_boundary_rejected():
    with pytest.raises(ValidationError):project(boundary=[(0,0),(8000,6000),(8000,0),(0,6000)])
def test_editable_door_real_sector():
    from app.models import Door
    d=Door(id='D-2',x=0,y=0,width=1000,angle=0,sweep=90)
    assert door_sweep(d).area==pytest.approx(3.14159*1000000/4,rel=.001)
    # An object in the bounding square but outside the sector is not blocked.
    p=project([item(x=900,y=900,width=50,depth=50,working=0)],doors=[d])
    assert not any(f['rule_id']=='GEO-OBSTACLE' for f in errors(p))
def test_editable_obstacle_and_overhead():
    o={'id':'OVERHEAD','kind':'overhead','x':1000,'y':0,'width':1000,'depth':1200,'bottom':2800,'top':3000}
    assert not errors(project(obstacles=[o]))
    o['bottom']=1000
    assert any(f['rule_id']=='GEO-OBSTACLE' for f in errors(project(obstacles=[o])))
def test_room_height():assert any(f['rule_id']=='HEIGHT-ROOM' for f in errors(project([item(height=3500)])))
@pytest.mark.parametrize('side',['front','rear','left','right'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_directional_envelope_is_separate(side,rotation):
    e=item(rotation=rotation,x=3000,y=3000);z=side_zone(e,side,300)
    assert z.area>0
    assert z.intersection(footprint(e)).area==0
def test_hard_and_soft_service():
    e=item(zones=[Zone(id='service',kind='service',side='rear',distance=300,hard=True,source='Guide p4')])
    assert any(f['rule_id']=='ZONE-SERVICE' for f in errors(project([e])))
    e.zones[0].hard=False
    assert not any(f['rule_id']=='ZONE-SERVICE' for f in errors(project([e])))
def test_future_region_blocks_footprints():
    p=project();p.regions=[__import__('app.models',fromlist=['Region']).Region(id='reserve',name='Future',x=900,y=0,width=1000,depth=1000,kind='future',hard=True)]
    assert not valid_static(p,p.equipment[0])
def test_rigid_assembly_solver():
    p=project([item(group='LINEUP'),item(id='PP-2',x=1700,group='LINEUP')])
    result=solve(p,Settings(grid_mm=100,max_time_seconds=10,return_limit=1))
    assert result['layouts']
    a,b=result['layouts'][0]['equipment']
    assert b['x']-a['x']==700
    assert a['rotation']==b['rotation']==0
def test_repair_fixes_unselected():
    p=project([item(),item(id='PP-2',x=1100)])
    result=solve(p,Settings(grid_mm=100,max_time_seconds=5,mode='repair',selected_ids=['PP-2'],return_limit=1))
    assert result['layouts']
    assert result['layouts'][0]['equipment'][0]['x']==1000
    assert not errors(p.model_copy(update={'equipment':[Equipment.model_validate(e) for e in result['layouts'][0]['equipment']]}))
def test_inner_orthogonal_walls_have_candidates():
    p=project(boundary=[(0,0),(8000,0),(8000,4000),(5000,4000),(5000,6000),(0,6000)])
    assert candidates(p,item(wall='north'),100)
def test_pdf_vector_output_and_underlay_render():
    from pypdf import PdfReader
    data=export_pdf(project());pdf=PdfReader(io.BytesIO(data))
    assert len(pdf.pages)>=3
    assert 'SCALE' in pdf.pages[0].extract_text()
    result=import_underlay('data:application/pdf;base64,'+base64.b64encode(data).decode())
    assert result['data'].startswith('data:image/jpeg;base64,')
def test_xlsx_unit_schedule():
    from openpyxl import load_workbook
    book=load_workbook(io.BytesIO(export_xlsx(project())))
    assert book.active.cell(1,4).value=='X (in)'
    assert book.active.cell(2,4).value==pytest.approx(1000/25.4)
    assert 'Validation' in book.sheetnames
def test_dxf_import_units_and_room():
    result=import_dxf(export_dxf(project()))
    assert result['room']['width']==pytest.approx(8000)
    assert result['room']['depth']==pytest.approx(6000)
def test_source_fields_roundtrip():
    p=project([item(source='Guide rev B page 4',manufacturer='Example',model='EX',definition='LIB-1')])
    p.scenarios=[{'name':'Baseline','equipment':[e.model_dump() for e in p.equipment]}]
    restored=Project.model_validate_json(p.model_dump_json())
    assert restored.equipment[0].source=='Guide rev B page 4'
    assert restored.scenarios[0]['name']=='Baseline'

def test_manufacturer_top_envelope_is_height_aware():
    e=item(height=2000,zones=[Zone(id='top',kind='ventilation',side='top',distance=500,hard=True,source='Guide')])
    p=project([e],obstacles=[{'id':'DUCT','kind':'overhead','x':1000,'y':0,'width':1000,'depth':500,'bottom':2300,'top':2500}])
    assert any(f['rule_id']=='ZONE-VENTILATION' for f in errors(p))
    assert not valid_static(p,e)

def test_planar_access_connected_and_blocked():
    door={'id':'EXIT','x':3300,'y':0,'width':1100,'angle':0,'sweep':90,'egress':True}
    p=project([item(x=1000,y=4500,rotation=180)],doors=[door],check_access=True,access_width=914.4)
    assert not any(f['rule_id']=='PROJECT-ACCESS-CONNECTIVITY' for f in errors(p))
    p.room.obstacles=[__import__('app.models',fromlist=['Obstacle']).Obstacle(id='BARRIER',x=0,y=2000,width=8000,depth=300,bottom=0,top=3048)]
    assert any(f['rule_id']=='PROJECT-ACCESS-CONNECTIVITY' for f in errors(p))

def test_rigid_replacement_route_and_missing_door():
    from app.replacement import study
    door={'id':'EXIT','x':3300,'y':0,'width':1100,'angle':0,'sweep':90,'egress':True}
    p=project(doors=[door])
    result=study(p,'PP-1',650,250,0,5)
    assert result['status']=='PASSED_IMPLEMENTED_STUDY'
    assert result['path']
    p.room.doors=[]
    assert study(p,'PP-1',650,250)['status']=='UNRESOLVED'

def test_cancelled_solver_does_not_mutate_project():
    p=project();before=p.model_dump_json();event=threading.Event();event.set()
    result=solve(p,Settings(),event)
    assert result['status']=='CANCELLED'
    assert before==p.model_dump_json()
