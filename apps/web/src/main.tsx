import React from 'react';
import {createRoot} from 'react-dom/client';
import {App} from './App';
class RecoveryBoundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 render(){if(!this.state.failed)return this.props.children;return <div style={{padding:40,fontFamily:'Segoe UI, sans-serif',maxWidth:600,margin:'10vh auto'}}><h1>The editor needs to reopen</h1><p>Your last completed autosave is still available. Reopen it to resume planning.</p><button onClick={()=>location.reload()}>Reopen saved layout</button><button onClick={()=>{const text=localStorage.getItem('fieldwork-project')||'{}',url=URL.createObjectURL(new Blob([text],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='fieldwork-recovery.ero.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),500);}}>Download saved project</button></div>;}
}
createRoot(document.getElementById('root')!).render(<RecoveryBoundary><App/></RecoveryBoundary>);
