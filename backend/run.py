"""Local launcher. Uses installed dependencies, or the workspace dependency target."""
import sys,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
deps=root.parents[1]/'work'/'python-deps'
if deps.exists(): sys.path.insert(0,str(deps))
sys.path.insert(0,str(root/'backend'))
os.chdir(root)
if __name__=='__main__':
    import uvicorn
    from app.main import app
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8765,log_level='warning'))
    app.state.shutdown=lambda:setattr(server,'should_exit',True)
    server.run()
