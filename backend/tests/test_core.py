import io,json,copy
import pytest
from pydantic import ValidationError
from shapely import affinity
from fastapi.testclient import TestClient
from app.models import Project,Equipment,Settings
from app.geometry import footprint,working_zone,room_polygon,overlap,valid_static,dimensions
from app.rules import validate
from app.solver import solve
from app.persistence import Store
from app.exporters import export_dxf,export_report
from app.main import app,SESSION_TOKEN

def item(**kw):
    return Equipment(**dict({'id':'PP-1','name':'Panel','category':'panelboard','x':1000,'y':0,'width':650,'depth':250,'working':1000,'rear':0,'voltage':120,'status':'verified'},**kw))
def project(equipment=None,**room):
    return Project(name='Test',room={'width':8000,'depth':6000,'column':False,**room},equipment=equipment if equipment is not None else [item()])
def errors(p):return [f for f in validate(p)['diagnostics'] if f['severity']=='error']

@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('width,depth',[(650,250),(1800,800),(1100,850),(800,500)])
def test_rotation_area_and_front_separation(rotation,width,depth):
    e=item(rotation=rotation,width=width,depth=depth,x=2500,y=2500)
    f,z=footprint(e),working_zone(e)
    assert f.area==width*depth
    assert z.area==max(width,762)*e.working
    assert not overlap(f,z)
    assert affinity.rotate(f,360).equals_exact(f,1e-8)

@pytest.mark.parametrize('x,y',[(56,0),(100,200),(500,300),(1000,0),(5000,0),(7000,0)])
def test_open_wall_valid(x,y):assert not errors(project([item(x=x,y=y)]))

@pytest.mark.parametrize('x,y,rotation',[(-1,0,0),(7800,0,0),(1000,5900,0),(0,1000,90),(1000,0,180),(7900,1000,270)])
def test_outside_footprint_or_clearance_rejected(x,y,rotation):assert errors(project([item(x=x,y=y,rotation=rotation)]))

def test_shared_working_zones_allowed():
    p=project([item(x=1000),item(id='PP-2',x=1660)])
    assert overlap(working_zone(p.equipment[0]),working_zone(p.equipment[1]))
    assert not errors(p)
def test_column_blocks_working_space():
    assert any(f['rule_id']=='GEO-OBSTACLE' for f in errors(project([item(x=3550,y=2000)],column=True)))
def test_door_blocks_equipment():assert errors(project([item(x=3400,y=0)]))
def test_equipment_collision():assert any(f['rule_id']=='GEO-COLLISION' for f in errors(project([item(),item(id='PP-2')])) )
def test_manufacturer_rear_clearance():assert any(f['rule_id']=='MFR-REAR' for f in errors(project([item(rear=200)])))
def test_rear_unknown_never_passes_silently():assert any(f['rule_id']=='MFR-REAR-UNKNOWN' for f in validate(project([item(rear=None)]))['diagnostics'])
def test_short_working_depth_rejected():assert any(f['rule_id']=='NEC2023-110.26-A1' for f in errors(project([item(working=900)])))
@pytest.mark.parametrize('condition,required',[(1,914),(2,1067),(3,1219)])
def test_depth_condition_boundaries(condition,required):
    assert not errors(project([item(voltage=277,condition=condition,working=required)]))
    assert errors(project([item(voltage=277,condition=condition,working=required-1)]))
def test_unsupported_voltage_unresolved():assert any(f['rule_id']=='NEC-VOLTAGE-UNSUPPORTED' for f in validate(project([item(voltage=1000)]))['diagnostics'])
def test_l_room_notch():assert not valid_static(project(notch=1500),item(x=7000,y=5000))
def test_unit_roundtrip():
    p=project();p.units='ft';assert Project.model_validate_json(p.model_dump_json()).equipment[0].width==650
def test_unique_ids_required():
    with pytest.raises(ValidationError):project([item(),item()])
def test_architecture_must_contain_door():
    with pytest.raises(ValidationError):project(width=3000)
def test_persistence_parent_revisions(tmp_path):
    store=Store(tmp_path/'test.sqlite3');p=project();one=store.save(p);p.name='Revised';two=store.save(p,one['id'])
    assert two['revision']>one['revision'];assert store.load(one['id'])['name']=='Revised'
def test_dxf_roundtrip():
    import ezdxf
    d=ezdxf.read(io.StringIO(export_dxf(project())))
    assert d.units==1
    assert len(d.modelspace().query('LWPOLYLINE[layer=="E-EQPM"]'))==1
    poly=list(d.modelspace().query('LWPOLYLINE[layer=="E-EQPM"]'))[0]
    assert max(pt[0] for pt in poly.get_points())-min(pt[0] for pt in poly.get_points())==pytest.approx(650/25.4)

def test_imperial_fraction_preserved_through_solver():
    p=project([item(width=1079.5,depth=508.0,x=1016.0,locked=True)])
    roundtrip=Project.model_validate_json(p.model_dump_json())
    assert roundtrip.equipment[0].width==1079.5
    result=solve(roundtrip,Settings(grid_mm=25.4,max_time_seconds=5,return_limit=1))
    assert result['layouts'][0]['equipment'][0]['width']==1079.5
    assert result['layouts'][0]['equipment'][0]['x']==1016.0

def test_imperial_report():
    result=export_report(project([item(width=914.4,working=762)]))
    assert result['units']=='imperial'
    assert result['equipment_schedule'][0]['width_in']==36
    assert not any(' mm' in f['message'] for f in result['validation']['diagnostics'])
def test_solver_locked_and_repeatable():
    p=project([item(locked=True),item(id='PP-2',x=2000,wall='north')]);s=Settings(grid_mm=100,max_time_seconds=5,return_limit=1)
    a,b=solve(p,s),solve(p,s)
    assert a['layouts'] and b['layouts']
    assert a['layouts'][0]['equipment']==b['layouts'][0]['equipment']
    locked=next(e for e in a['layouts'][0]['equipment'] if e['id']=='PP-1')
    assert locked==p.equipment[0].model_dump()
    assert not errors(p.model_copy(update={'equipment':[Equipment.model_validate(e) for e in a['layouts'][0]['equipment']]}))
def test_solver_zero_domain_explained():
    r=solve(project([item(x=-1000,locked=True)]),Settings())
    assert not r['layouts'];assert 'PP-1' in r['diagnostics'][0]
def test_solver_distinct_alternatives():
    p=project([item(wall='any')]);r=solve(p,Settings(max_time_seconds=5))
    assert len(r['layouts'])==3
    assert len({json.dumps(a['equipment'],sort_keys=True) for a in r['layouts']})==3
    assert all(not errors(p.model_copy(update={'equipment':[Equipment.model_validate(e) for e in a['equipment']]})) for a in r['layouts'])
def test_api_validation_and_security():
    client=TestClient(app);p=project().model_dump()
    assert client.get('/api/v1/health').status_code==200
    assert client.post('/api/v1/validate',json=p).status_code==401
    assert client.get('/api/v1/session',headers={'Origin':'https://foreign.example'}).status_code==403
    assert client.get('/api/v1/session',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert client.get('/api/v1/session',headers={'Host':'foreign.example'}).status_code==403
    r=client.post('/api/v1/validate',json=p,headers={'X-Session-Token':SESSION_TOKEN})
    assert r.status_code==200;assert r.json()['status']=='passed_implemented_checks_with_unresolved_items'
def test_api_project_roundtrip():
    client=TestClient(app);h={'X-Session-Token':SESSION_TOKEN};p=project().model_dump()
    r=client.post('/api/v1/projects',json=p,headers=h);assert r.status_code==200
    assert client.get('/api/v1/projects/'+r.json()['id']).json()==p
