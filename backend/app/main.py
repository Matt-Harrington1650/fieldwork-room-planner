"""Loopback-only application boundary; no engineering logic in routes."""
import os,secrets,json,threading,sys
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import JSONResponse,Response
from fastapi.staticfiles import StaticFiles
from .models import Project,SolveRequest
from .rules import validate,PACK,UNIMPLEMENTED
from .solver import solve
from .persistence import Store
from .exporters import export_dxf,export_report
from .deliverables import export_pdf,export_xlsx
from .importers import import_dxf,import_underlay
from .replacement import study

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[2]))
SESSION_TOKEN=secrets.token_urlsafe(32)
store=Store(os.environ.get('FIELDWORK_DB',str((Path(os.environ.get('LOCALAPPDATA',str(ROOT)))/'Fieldwork' if getattr(sys,'frozen',False) else ROOT/'data')/'projects.sqlite3')))
solve_lock=threading.Lock()
jobs={}
app=FastAPI(title='Fieldwork local engineering API',version='0.1.0')

@app.middleware('http')
async def secure_local_api(request:Request,call_next):
    host=request.url.hostname
    if host not in ['127.0.0.1','localhost','testserver']:
        return JSONResponse({'detail':'Only loopback hosts are accepted.'},status_code=403)
    if request.url.path.startswith('/api/'):
        if request.headers.get('sec-fetch-site')=='cross-site':
            return JSONResponse({'detail':'Cross-site calls are not allowed.'},status_code=403)
        origin=request.headers.get('origin')
        if origin and origin not in ['http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8765','http://localhost:8765']:
            return JSONResponse({'detail':'Origin is not allowed.'},status_code=403)
        try:size=int(request.headers.get('content-length','0') or 0)
        except ValueError:return JSONResponse({'detail':'Invalid content length.'},status_code=400)
        if size>25_000_000:
            return JSONResponse({'detail':'Request exceeds 25 MB limit.'},status_code=413)
        if request.method not in ['GET','HEAD'] and not secrets.compare_digest(request.headers.get('X-Session-Token',''),SESSION_TOKEN):
            return JSONResponse({'detail':'Missing or invalid local session token.'},status_code=401)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store' if request.url.path.startswith('/api/') else 'no-cache'
    return response

@app.get('/api/v1/health')
def health():return {'status':'ready','application':'Fieldwork','version':'0.2.0','coordinate_unit':'mm'}
@app.get('/api/v1/session')
def session():return {'token':SESSION_TOKEN}
@app.post('/api/v1/shutdown')
def shutdown():
    callback=getattr(app.state,'shutdown',None)
    if callback:callback()
    return {'stopping':bool(callback)}
@app.get('/api/v1/rulepacks')
def packs():return [{'id':PACK,'reviewed':False,'unimplemented':UNIMPLEMENTED}]
@app.post('/api/v1/validate')
def validate_project(project:Project):return validate(project)
@app.post('/api/v1/solve')
def solve_project(request:SolveRequest):
    if not solve_lock.acquire(blocking=False):raise HTTPException(409,'Another local solve is running.')
    try:
        cancel=threading.Event();jobs[request.settings.job_id]=cancel
        result=solve(request.project,request.settings,cancel);store.record_solve(result);return result
    finally:
        jobs.pop(request.settings.job_id,None)
        solve_lock.release()

@app.post('/api/v1/solve/cancel')
def cancel_solve(body:dict):
    event=jobs.get(body.get('job_id',''))
    if event:event.set()
    return {'cancel_requested':bool(event)}

@app.post('/api/v1/replacement')
def replacement(body:dict):
    try:return study(Project.model_validate(body['project']),str(body['equipment_id']),float(body['width']),float(body['depth']),float(body.get('allowance',0)))
    except Exception as e:raise HTTPException(422,str(e))
@app.post('/api/v1/projects')
def create_project(project:Project):return store.save(project)
@app.get('/api/v1/projects/{project_id}')
def get_project(project_id:str):
    result=store.load(project_id)
    if result is None:raise HTTPException(404,'Project not found.')
    return result
@app.put('/api/v1/projects/{project_id}')
def save_project(project_id:str,project:Project):
    if store.load(project_id) is None:raise HTTPException(404,'Project not found.')
    return store.save(project,project_id)
def require_room(project:Project):
    if not project.room.defined:raise HTTPException(422,'Draw a room outline or choose a room shape first.')

@app.post('/api/v1/export/dxf')
def dxf(project:Project):
    require_room(project)
    return Response(export_dxf(project),media_type='application/dxf',headers={'Content-Disposition':'attachment; filename=electrical-room.dxf'})
@app.post('/api/v1/export/report')
def report(project:Project):
    require_room(project)
    return export_report(project)

@app.post('/api/v1/export/pdf')
def pdf(project:Project):
    require_room(project)
    return Response(export_pdf(project),media_type='application/pdf')
@app.post('/api/v1/export/xlsx')
def xlsx(project:Project):
    require_room(project)
    return Response(export_xlsx(project),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
@app.post('/api/v1/import/dxf')
def read_dxf(body:dict):
    try:return import_dxf(body.get('text',''))
    except Exception as e:raise HTTPException(422,str(e))
@app.post('/api/v1/import/underlay')
def read_underlay(body:dict):
    try:return import_underlay(body.get('data',''))
    except Exception as e:raise HTTPException(422,'PDF could not be rendered: '+str(e))

@app.get('/api/v1/projects/{project_id}/revisions')
def revisions(project_id:str):
    with store.connect() as db:
        rows=db.execute('SELECT id,created_at,input_hash FROM revisions WHERE project_id=? ORDER BY id DESC LIMIT 100',(project_id,)).fetchall()
        return [{'id':r[0],'created_at':r[1],'input_hash':r[2]} for r in rows]
@app.get('/api/v1/projects/{project_id}/revisions/{revision_id}')
def revision(project_id:str,revision_id:int):
    with store.connect() as db:row=db.execute('SELECT payload FROM revisions WHERE project_id=? AND id=?',(project_id,revision_id)).fetchone()
    if not row:raise HTTPException(404,'Revision not found.')
    return json.loads(row[0])

if (ROOT/'dist').exists():app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='web')
