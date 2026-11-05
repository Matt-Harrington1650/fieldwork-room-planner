"""Build an offline unsigned Windows x64 application with PyInstaller."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
workspace_deps=root.parents[1]/'work'/'python-deps'
if workspace_deps.exists():sys.path.insert(0,str(workspace_deps))
import PyInstaller.__main__
args=['--noconfirm','--name','Fieldwork','--onedir','--windowed',
      '--distpath',str(root/'release'),'--workpath',str(root/'build'/'pyinstaller'),'--specpath',str(root/'build'),
      '--paths',str(root/'backend'),'--add-data',str(root/'dist')+';dist',
      '--collect-all','ortools','--collect-all','shapely','--collect-all','pypdfium2','--collect-all','pypdfium2_raw','--copy-metadata','fastapi',
      '--hidden-import','uvicorn.logging','--hidden-import','uvicorn.loops.auto','--hidden-import','uvicorn.protocols.http.auto','--hidden-import','uvicorn.protocols.websockets.auto','--hidden-import','uvicorn.lifespan.on',
      '--exclude-module','matplotlib','--exclude-module','scipy','--exclude-module','torch','--exclude-module','tensorflow','--exclude-module','IPython','--exclude-module','pytest','--exclude-module','tkinter','--exclude-module','cv2']
if workspace_deps.exists():args+=['--paths',str(workspace_deps)]
args+=[str(root/'backend'/'desktop.py')]
PyInstaller.__main__.run(args)
