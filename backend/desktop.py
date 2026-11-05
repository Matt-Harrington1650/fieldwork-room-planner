"""Packaged local application launcher; no Python installation required after build."""
import os,sys,threading,time,webbrowser,socket
from pathlib import Path
if not getattr(sys,'frozen',False):
    root=Path(__file__).resolve().parents[1]
    deps=root.parents[1]/'work'/'python-deps'
    if deps.exists():sys.path.insert(0,str(deps))
    sys.path.insert(0,str(root/'backend'))

def launch_browser():
    import urllib.request
    for _ in range(80):
        try:
            urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health',timeout=.3)
            if os.environ.get('FIELDWORK_NO_BROWSER')!='1':webbrowser.open('http://127.0.0.1:8765')
            return
        except Exception:time.sleep(.25)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    if sys.stdout is None:sys.stdout=open(os.devnull,'w')
    if sys.stderr is None:sys.stderr=open(os.devnull,'w')
    sock=socket.socket();busy=sock.connect_ex(('127.0.0.1',8765))==0;sock.close()
    if busy:
        import urllib.request,json
        try:
            health=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health',timeout=2))
            if health.get('application')!='Fieldwork':raise ValueError('Another program is using the planner port.')
            if os.environ.get('FIELDWORK_NO_BROWSER')!='1':webbrowser.open('http://127.0.0.1:8765')
        except Exception:
            if os.environ.get('FIELDWORK_NO_BROWSER')!='1':
                import ctypes
                ctypes.windll.user32.MessageBoxW(0,'The planner could not start because its local port is in use. Close the other local service and try again.','Fieldwork',0)
        sys.exit(0)
    threading.Thread(target=launch_browser,daemon=True).start()
    import uvicorn
    from app.main import app
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8765,log_level='warning'))
    app.state.shutdown=lambda:setattr(server,'should_exit',True)
    server.run()
