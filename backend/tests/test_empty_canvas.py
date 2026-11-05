import pytest
from fastapi.testclient import TestClient
from app.main import app, SESSION_TOKEN
from app.models import Project, Settings
from app.geometry import room_points, room_polygon
from app.rules import validate
from app.solver import solve

def draft():
    return Project(name='Draw my own room',units='ft',room={'defined':False,'width':6096,'depth':4876.8,'doors':[],'obstacles':[],'column':False},equipment=[])

def test_undefined_room_has_no_geometry_or_clearance_pass():
    p=draft()
    assert room_points(p)==[]
    assert room_polygon(p).is_empty
    assert validate(p)['status']=='room_not_defined'
    assert solve(p,Settings())['status']=='NO_ROOM'
    assert Project(name='Legacy',room={'width':8000,'depth':6000},equipment=[]).room.defined is True

def test_empty_canvas_project_survives_database_roundtrip():
    client=TestClient(app)
    p=draft().model_dump()
    result=client.post('/api/v1/projects',json=p,headers={'X-Session-Token':SESSION_TOKEN})
    assert result.status_code==200
    restored=client.get('/api/v1/projects/'+result.json()['id']).json()
    assert restored==p
    assert restored['room']['defined'] is False

@pytest.mark.parametrize('kind',['pdf','dxf','report','xlsx'])
def test_plan_exports_wait_for_a_real_room(kind):
    response=TestClient(app).post('/api/v1/export/'+kind,json=draft().model_dump(),headers={'X-Session-Token':SESSION_TOKEN})
    assert response.status_code==422
    assert 'Draw a room' in response.json()['detail']
