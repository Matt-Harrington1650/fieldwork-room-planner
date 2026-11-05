import React,{useEffect,useState,useRef} from 'react';
import {formatLength,parseLength} from './imperial';
export function NumberField({value,onValue,min=-100000,max=100000,nullable=false,...props}:{value:number|null;onValue:(value:number|null)=>void;min?:number;max?:number;nullable?:boolean}&Omit<React.InputHTMLAttributes<HTMLInputElement>,'value'|'onChange'|'min'|'max'|'type'>){
 const [draft,setDraft]=useState(value===null?'':String(value));
 const cancelBlur=useRef(false);
 useEffect(()=>setDraft(value===null?'':String(value)),[value]);
 function finish(){if(cancelBlur.current){cancelBlur.current=false;return;}const text=draft.trim();if(text===''&&nullable){onValue(null);return;}const parsed=Number(text);if(text===''||!Number.isFinite(parsed)){setDraft(value===null?'':String(value));return;}const next=Math.max(min,Math.min(max,Math.round(parsed)));setDraft(String(next));if(next!==value)onValue(next);}
 return <input {...props} type="number" min={min} max={max} step="1" value={draft} onChange={e=>setDraft(e.target.value)} onBlur={finish} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();e.currentTarget.blur();}if(e.key==='Escape'){e.preventDefault();cancelBlur.current=true;setDraft(value===null?'':String(value));e.currentTarget.blur();}}}/>;
}
export function LengthField({value,onValue,min=-100000,max=100000,nullable=false,...props}:{value:number|null;onValue:(value:number|null)=>void;min?:number;max?:number;nullable?:boolean}&Omit<React.InputHTMLAttributes<HTMLInputElement>,'value'|'onChange'|'min'|'max'|'type'>){
 const label=value===null?'':formatLength(value);const [draft,setDraft]=useState(label);const [invalid,setInvalid]=useState(false);const cancelBlur=useRef(false);
 useEffect(()=>{setDraft(label);setInvalid(false);},[value,label]);
 function finish(){if(cancelBlur.current){cancelBlur.current=false;return;}if(draft===label)return;if(!draft.trim()&&nullable){onValue(null);setInvalid(false);return;}const parsed=parseLength(draft);if(parsed===null){setDraft(label);setInvalid(false);return;}const next=Math.max(min,Math.min(max,parsed));setDraft(formatLength(next));setInvalid(false);if(next!==value)onValue(next);}
 return <input {...props} type="text" aria-invalid={invalid||undefined} title={"Feet and inches; bare numbers are inches. Example: 3 ft 6 1/2 in"} value={draft} onChange={e=>{setDraft(e.target.value);setInvalid(Boolean(e.target.value)&&parseLength(e.target.value)===null);}} onBlur={finish} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();e.currentTarget.blur();}if(e.key==='Escape'){e.preventDefault();cancelBlur.current=true;setDraft(label);setInvalid(false);e.currentTarget.blur();}}}/>;
}
