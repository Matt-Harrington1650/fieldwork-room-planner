const MM_PER_INCH=25.4;
let displayPrecision=16;
export function configureImperialPrecision(precision:number){if([1,2,4,8,16,32,64].includes(precision))displayPrecision=precision;}
export const inchesToWorld=(inches:number)=>Math.round(inches*MM_PER_INCH*1e6)/1e6;
export const worldToInches=(mm:number)=>mm/MM_PER_INCH;
export function formatLength(mm:number,precision=displayPrecision):string{
 if(!Number.isFinite(mm))return '—';
 const ticks=Math.round(Math.abs(worldToInches(mm))*precision),feet=Math.floor(ticks/(12*precision)),whole=Math.floor(ticks%(12*precision)/precision),num=ticks%precision;
 let fraction='';if(num){let a=num,b=precision;while(b){const r=a%b;a=b;b=r;}fraction=` ${num/a}/${precision/a}`;}
 return `${mm<0&&ticks?'-':''}${feet}' ${whole}${fraction}"`;
}
export function parseLength(text:string):number|null{
 const s=text.trim().toLowerCase().replace(/[′’]/g,"'").replace(/[″“”]/g,'"').replace(/feet|foot|ft\.?/g,"'").replace(/inches|inch|in\.?/g,'"').replace(/\s+'/g,"'").replace(/'\s*-\s*/g,"' ");
 if(!s)return null;
 const sign=s.startsWith('-')?-1:1,t=s.replace(/^[+-]\s*/,'');
 function number(part:string){if(/^\d+(?:\.\d+)?$/.test(part))return Number(part);const m=part.match(/^(?:(\d+)\s+)?(\d+)\/(\d+)$/);return m&&+m[3]!==0?+(m[1]||0)+ +m[2]/+m[3]:NaN;}
 let inches:number;
 if(t.includes("'")){const m=t.match(/^(\d+(?:\.\d+)?)'\s*(.*?)\s*"?$/);if(!m)return null;const remainder=m[2].replace(/"$/,'').trim();inches=+m[1]*12+(remainder?number(remainder):0);}
 else inches=number(t.replace(/"$/,'').trim());
 return Number.isFinite(inches)?inchesToWorld(sign*inches):null;
}
export function imperialMessage(message:string){return message.replace(/(-?\d+(?:\.\d+)?)\s*mm\b/g,(_,n)=>formatLength(Number(n)));}
export const squareFeet=(areaMm2:number)=>areaMm2/(304.8*304.8);
