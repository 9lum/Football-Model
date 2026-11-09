'use client';
import {useId} from 'react';
import {fieldPoint,fieldPolygon,fieldBands} from '../../../web/field-perspective.mjs';
const depths=['short','intermediate','deep'],areas=['left','middle','right'];
const palette:Record<string,string>={short:'#55cbb0',intermediate:'#7bb5ff',deep:'#c4a0f2'};
const pct=(value:any)=>Number.isFinite(value)?Math.round(value*100)+'%':'—';
export default function FieldSurface({player,zones,selection,onSelect,depth,paths,qb}:any){
 const id=useId().replace(/:/g,'');
 const point=(x:number,z:number)=>fieldPoint(x,z,depth),polygon=(x0:number,z0:number,x1:number,z1:number)=>fieldPolygon(x0,z0,x1,z1,depth);
 const selectedDepth=selection.split('_')[0],selectedArea=areas.indexOf(selection.split('_')[1]);
 const band=(fieldBands as any)[selectedDepth]||fieldBands.short,end=point(18+selectedArea*32,(band[0]+band[1])/2),start=point(50,7);
 return <div className={'receiving-field-stage'+(depth?' tilted':'')} data-view={depth?'end-zone':'overhead'}>
  <svg viewBox="0 45 720 420" role="group" aria-label={player.name+(qb?' passing':' target')+' distribution; '+(depth?'elevated end-zone perspective':'overhead view')+'; select a zone to inspect'}>
   <defs><linearGradient id={id+'-grass'} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1c4f50"/><stop offset="1" stopColor="#102e39"/></linearGradient><linearGradient id={id+'-edge'} x1="0" y1="0" x2="0" y2="1"><stop stopColor="#39716e"/><stop offset="1" stopColor="#0a1b26"/></linearGradient></defs>
   {depth&&<g className="field-stadium-seating" aria-hidden="true">{[9,6,3].map((n,i)=><polygon key={n} points={polygon(-n,-n/2,100+n,64+n/2)} fill={i===0?'#152b35':'#223e47'} fillOpacity={.65} stroke="#7faaa9" strokeOpacity={.18+i*.06} strokeWidth="1.5"/>)}<polygon points={polygon(0,0,100,64).split(' ').slice(0,2).join(' ')+' '+[point(100,0),point(0,0)].map(p=>`${p.x},${p.y+10}`).join(' ')} fill={'url(#'+id+'-edge)'} stroke="#345b61" strokeWidth="1"/></g>}
   <polygon points={polygon(0,0,100,64)} fill={'url(#'+id+'-grass)'} stroke="#86bcb6" strokeWidth="1.8"/>
   {Array.from({length:10},(_,i)=><polygon key={i} points={polygon(0,8+i*5,100,13+i*5)} fill="#bde9db" fillOpacity={i%2===0 ? .035 : 0} pointerEvents="none"/>)}
   {[0,58].map(z=><polygon key={z} points={polygon(1,z,99,z+6)} fill="#5fc3b3" fillOpacity=".14"/>)}
   {[0,10,20,30,40,50].map(yards=>{const z=8+yards,l=point(1,z),r=point(99,z),label=point(3,z);return <g key={yards}><line x1={l.x} y1={l.y} x2={r.x} y2={r.y} stroke="#b8dcd7" strokeOpacity=".28"/><text x={label.x} y={label.y-5} fill="#bfdbd6" fontSize="11" textAnchor="start">{yards}</text></g>})}
   {Array.from({length:24},(_,i)=>[38,62].map(x=>{const a=point(x,9+i*2),b=point(x+1.2,9+i*2);return <line key={i+'-'+x} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#bfdbd6" strokeOpacity=".2"/>}))}
   {depths.flatMap(d=>areas.map((area,i)=>{
    const key=d+'_'+area,zone=zones.find((z:any)=>z.depth===d&&z.area===area),active=selection===key,[near,far]=(fieldBands as any)[d];
    const x0=7+i*29.5,x1=x0+27,inset=d==='intermediate' ? .8 : 1.2,nearInset=near+inset,farInset=far-inset;
    const front=point((x0+x1)/2,nearInset),back=point((x0+x1)/2,farInset),cx=(front.x+back.x)/2,cy=(front.y+back.y)/2;
    return <g key={key} className={'receiving-field-zone field-zone-'+d+(active?' selected':'')} role="button" tabIndex={0} aria-pressed={active} aria-label={d+' '+area+': '+pct(zone?.targetShare)} onClick={()=>onSelect(key)} onFocus={()=>onSelect(key)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(key)}}}>
     <title>{d} {area}: {zone?.targets??0} {qb?'passes':'targets'} · {pct(zone?.targetShare)}</title>
     <polygon points={polygon(x0,nearInset,x1,farInset)} fill={palette[d]} fillOpacity={active ? .3 : .13} stroke={palette[d]} strokeWidth={active?2.2:1.2} strokeOpacity={active?1:.6}/>
     <text className="field-zone-percentage" x={cx} y={cy-(d==='intermediate'?7:8)} textAnchor="middle" dominantBaseline="central" fill="#f2fbff" fontSize="26" fontWeight="600">{Number.isFinite(zone?.targetShare)?<><tspan>{Math.round(zone.targetShare*100)}</tspan><tspan className="field-zone-percent-symbol" fontSize="15" dx="2">%</tspan></>:'—'}</text>
     <text className="field-zone-depth" x={cx} y={cy+(d==='intermediate'?17:20)} textAnchor="middle" fill="#bfd5de" fontSize={d==='intermediate'?9:10}>{d==='short'?'Under 10 yd':d==='intermediate'?'10–19 yd':'20+ yd'}</text>
    </g>;
   }))}
   {paths&&<path d={`M ${start.x} ${start.y} Q ${start.x} ${end.y+35} ${end.x} ${end.y}`} fill="none" stroke={palette[selectedDepth]} strokeWidth="2.5" strokeDasharray="6 5" pointerEvents="none"/>}
   <line x1={point(2,8).x} y1={point(2,8).y} x2={point(98,8).x} y2={point(98,8).y} stroke="#f1d58c" strokeWidth="2" strokeDasharray="6 4"/>
   <text x={point(50,3).x} y={point(50,3).y+4} textAnchor="middle" fill="#d5e6e7" fontSize="11" letterSpacing=".4">Line of scrimmage ↑</text>
   <text x={point(50,61).x} y={point(50,61).y+4} textAnchor="middle" fill="#d5e6e7" fontSize="10" letterSpacing=".8">Upfield ↑</text>

  </svg>
  <div className="field-column-labels" aria-hidden="true">{areas.map(area=><span key={area}>{area}</span>)}</div>
  <p className="field-view-caption">{depth?'Elevated end-zone view':'Overhead view'}<span>Illustrative field</span></p>
 </div>;
}
