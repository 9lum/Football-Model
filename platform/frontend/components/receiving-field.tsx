'use client';
import {useId,useRef,useState} from 'react';
import './receiving-field.css';
import {impliedTeamPoints,matchGameMarket} from '../../../web/game-markets.mjs';
import {teamNames} from '../../../web/market-core.mjs';
const pct=(n:any)=>Number.isFinite(n)?Math.round(n*100)+'%':'—';
const num=(n:any,d=1)=>Number.isFinite(n)?Number(n).toFixed(d):'—';
const depths=['short','intermediate','deep'],areas=['left','middle','right'];
const palette:Record<string,string>={short:'#55cbb0',intermediate:'#7bb5ff',deep:'#c4a0f2'};
const geometry:Record<string,{y:number,h:number}>={short:{y:247,h:48},intermediate:{y:197,h:48},deep:{y:47,h:148}};
export default function ReceivingField({player,forecast,research,events=[]}:any){
 const [period,setPeriod]=useState('last6'),[zoneSelection,setSelection]=useState(''),[tilted,setTilted]=useState(true),[paths,setPaths]=useState(false);
 const field=useRef<HTMLDivElement>(null),gradient=useId().replace(/:/g,'');
 if(!['WR','TE','RB','QB'].includes(player?.position))return null;
 const qb=player.position==='QB',base=player.receivingRouteProfile;
 const source=research&&(!base||!Number.isFinite(Date.parse(base.last6?.asOf||''))||Date.parse(research.last6?.asOf||'')>=Date.parse(base.last6?.asOf||''))?research:base;
 const profile=source?.[period]||(!qb&&period==='last6'?forecast?.routeMatchup?.profile:null),available=profile?.status==='available';
 const zones=profile?.zones||[],selection=zoneSelection||[...zones].sort((a:any,b:any)=>b.targets-a.targets).map((z:any)=>z.depth+'_'+z.area)[0]||'short_middle';
 const selected=zones.find((z:any)=>z.depth+'_'+z.area===selection),context=!qb?forecast?.routeMatchup:null;
 const market=impliedTeamPoints(matchGameMarket(events,forecast,teamNames),(teamNames as Record<string,string>)[player.team]||player.team);
 const concepts=(profile?.routeTypes||[]).filter((r:any)=>r.verified===true&&Number.isFinite(r.share)&&r.share>=0&&r.share<=1&&r.samples>0&&typeof r.name==='string'&&typeof r.source==='string'&&r.source.startsWith('https://'));
 const items=qb?[
  ['Pass attempts',profile?.throwAttempts,0],['Completion rate',profile?.completionRate,'pct'],['Average air depth',profile?.adot,1],
  ['Yards / attempt',profile?.yardsPerAttempt,2],['EPA / dropback',profile?.epaPerDropback,2],['CPOE',profile?.cpoe,'points']
 ]:[['Located targets',profile?.targets,0],['Located catches',profile?.receptions,0],['Located receiving yards',profile?.receivingYards,0],['Average air depth',profile?.adot,1],['Yards / target',profile?.yardsPerTarget,2],['Catch rate',profile?.catchRate,'pct']];
 return <section className="receiving-field-panel" aria-label={qb?'Quarterback passing field and rushing profile':'Receiving field and target-depth research'}>
  <header className="receiving-field-heading">
   <div><span className="eyebrow">{qb?'QUARTERBACK PROFILE':'RECEIVING PROFILE'}</span><h3>{qb?'Where the passes go':'Where the targets go'}</h3><p>{qb?'Throwing depth, field location & rushing decisions':'Target depth & field location · measured play-by-play'}</p></div>
   <div className="receiving-field-controls"><label>Sample<select value={period} onChange={e=>{setPeriod(e.target.value);setSelection('')}}>{[3,6,9].map(n=><option key={n} value={'last'+n}>Last {n} {qb?'games':'targeted games'}</option>)}<option value="season">Current season</option></select></label><button aria-pressed={tilted} onClick={()=>setTilted(v=>!v)}>{tilted?'Depth on':'Flat field'}</button><button aria-pressed={paths} onClick={()=>setPaths(v=>!v)}>Example path {paths?'on':'off'}</button></div>
  </header>
  {available?<>
   <div className="receiving-field-layout"><div className="receiving-field-map">
    <div ref={field} className={'receiving-field-stage'+(tilted?' tilted':'')} onPointerMove={e=>{if(tilted&&e.pointerType==='mouse'){const box=e.currentTarget.getBoundingClientRect();field.current?.style.setProperty('--field-yaw',((e.clientX-box.left)/box.width*4-2)+'deg')}}} onPointerLeave={()=>field.current?.style.setProperty('--field-yaw','0deg')}>
     <svg viewBox="0 0 600 348" role="group" aria-label={player.name+(qb?' passing':' target')+' distribution; select a zone to inspect'}>
      <defs><linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#153e43"/><stop offset="1" stopColor="#102c36"/></linearGradient></defs>
      <rect x="10" y="10" width="580" height="320" rx="12" fill={'url(#'+gradient+')'} stroke="#75aaa7" strokeWidth="1.5"/>
      <rect x="22" y="18" width="556" height="22" rx="4" fill="#4bc9b1" fillOpacity=".1"/>
      <text x="300" y="33" textAnchor="middle" fill="#d2eee9" fontSize="11" letterSpacing="2">ATTACKING END ZONE ↑</text>
      {[46,96,146,196,246,296].map((y,i)=><g key={y}><line x1="24" x2="576" y1={y} y2={y} stroke="#b8dcd7" strokeOpacity=".24"/><text x="32" y={y-5} fill="#c1deda" fontSize="11">{50-i*10}</text></g>)}
      {Array.from({length:24},(_,i)=><g key={i}>{[226,374].map(x=><line key={x} x1={x} x2={x+6} y1={51+i*10} y2={51+i*10} stroke="#c1deda" strokeOpacity=".16"/>)}</g>)}
      {depths.flatMap(depth=>areas.map((area,i)=>{const zone=zones.find((z:any)=>z.depth===depth&&z.area===area),key=depth+'_'+area,g=geometry[depth],x=65+i*160,active=selection===key;return <g key={key} className={'receiving-field-zone'+(active?' selected':'')} role="button" tabIndex={0} aria-pressed={active} aria-label={depth+' '+area+': '+pct(zone?.targetShare)} onClick={()=>setSelection(key)} onFocus={()=>setSelection(key)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelection(key)}}}>
       <title>{depth} {area}: {zone?.targets||0} {qb?'passes':'targets'} · {pct(zone?.targetShare)}</title>
       <rect x={x} y={g.y} width="150" height={g.h} rx="6" fill={palette[depth]} fillOpacity={active ? .24 : .09} stroke={palette[depth]} strokeWidth={active?2:1} strokeOpacity={active?1:.4}/>
       <text x={x+75} y={g.y+g.h/2-1} textAnchor="middle" fill="#f4fbff" fontSize="26" fontWeight="650">{pct(zone?.targetShare)}</text>
       <text x={x+75} y={g.y+g.h/2+16} textAnchor="middle" fill="#d6e3ec" fontSize="11">{depth==='intermediate'?'10–19':depth==='deep'?'20+':'under 10'} air yards</text>
      </g>}))}
      {paths&&<path d={'M 300 305 C 300 270 '+(145+areas.indexOf(selection.split('_')[1])*160)+' 260 '+(140+areas.indexOf(selection.split('_')[1])*160)+' '+(geometry[selection.split('_')[0]].y+geometry[selection.split('_')[0]].h/2)} fill="none" stroke={palette[selection.split('_')[0]]} strokeWidth="2.5" strokeDasharray="7 5" pointerEvents="none"/>}
      <line x1="65" x2="535" y1="296" y2="296" stroke="#f1d58c" strokeWidth="2" strokeDasharray="5 4"/>
      <text x="300" y="317" fill="#d3e1e4" fontSize="11" textAnchor="middle">LINE OF SCRIMMAGE · ILLUSTRATIVE FIELD</text>
      {areas.map((area,i)=><text key={area} x={140+i*160} y="344" fill="currentColor" fontSize="11" fontWeight="600" textAnchor="middle">{area.toUpperCase()}</text>)}
     </svg>
    </div>
    <div className="receiving-depth-legend">{depths.map(depth=><button key={depth} onClick={()=>setSelection(depth+'_middle')}><i style={{background:palette[depth]}}/><span>{depth==='short'?'Short':depth==='deep'?'Deep':'Intermediate'}</span><strong>{pct(profile.depthShares?.[depth])}</strong></button>)}</div>
    <p className="receiving-field-hint">Select a zone to inspect · percentages of located {qb?'throws':'targets'}{paths?' · example path, not tracking':''}</p>
   </div>
   <aside className="receiving-zone-evidence"><div className="receiving-zone-title"><div><span className="eyebrow">SELECTED ZONE</span><h4>{selection.replace('_',' ')}</h4></div><strong className="receiving-zone-share" style={{color:palette[selection.split('_')[0]]}}>{pct(selected?.targetShare)}</strong></div>
    <dl>{[[qb?'Passes':'Targets',selected?.targets??'—'],[qb?'Completion rate':'Catch rate',pct(selected?.catchRate)],[qb?'Yards / attempt':'Yards / target',num(selected?.yardsPerTarget,2)],[qb?'EPA / attempt':'EPA / target',num(selected?.epaPerTarget,2)],['Air depth',num(selected?.airYards)+' yd']].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    <p>{profile.games} games · {qb?profile.locatedAttempts:profile.targets} located {qb?'throws':'targets'}</p>
   </aside></div>
   <dl className="receiving-field-stats">{items.map(([label,value,d]:any)=><div key={label}><dt>{label}</dt><dd>{d==='pct'?pct(value):d==='points'?Number.isFinite(value)?num(value)+' pp':'—':num(value,d)}</dd></div>)}</dl>
  </>:<p className="receiving-chart-definition">No matched {qb?'passing':'target'} locations are available for this sample yet. Missing locations and route concepts are not estimated.</p>}
  {qb&&Number.isFinite(profile?.dropbacks)&&<section className="qb-rushing-profile"><header><h4>Scramble & designed-run usage</h4><span>{profile.dropbacks} dropbacks · kneels excluded</span></header><div className="qb-rushing-grid"><div><span>Scramble rate</span><strong>{pct(profile.scrambleRate)}</strong><small>{profile.scrambles??'—'} scrambles / {profile.dropbacks} dropbacks</small></div><div><span>Scramble yards</span><strong>{num(profile.scrambleYards,0)}</strong><small>Recorded rushing yards</small></div><div><span>Designed carries</span><strong>{num(profile.designedRushAttempts,0)}</strong><small>{pct(profile.designedRushShare)} of non-kneel QB carries</small></div><div><span>Designed-run yards</span><strong>{num(profile.designedRushYards,0)}</strong><small>Non-scramble rushing yards</small></div></div></section>}
  {profile?.asOf&&<p className="receiving-chart-definition">{profile.definition} Through {new Date(profile.asOf).toLocaleDateString()}. <a href={profile.source} target="_blank" rel="noreferrer">Play-by-play source ↗</a></p>}
  {!qb&&<details className="receiving-route-concepts"><summary>Route types & coverage context</summary>{concepts.length?<div className="receiving-concept-bars">{concepts.map((r:any,i:number)=><div key={r.name}><header><strong>{r.name}</strong><span>{pct(r.share)}</span></header><div><i style={{width:pct(r.share),background:palette[depths[i%3]]}}/></div><small>{r.samples} charted routes · <a href={r.source} target="_blank" rel="noreferrer">Source ↗</a></small></div>)}</div>:<p>Verified slant, out, curl, post and go-route shares are unavailable in this feed. The field shows target locations, not percentages of routes run.</p>}{context?.coverageEfficiency&&<div className="receiving-coverage-grid">{['man','zone'].map(type=>{const c=context.coverageEfficiency[type];return <div key={type}><strong>Historical vs {type}</strong><span>{c?.targets??0} labeled targets</span><span>{num(c?.yardsPerTarget,2)} yards / target</span><span>{pct(c?.catchRate)} catch rate</span></div>})}</div>}<p>{context?.coverageEfficiencyScope||'Season route totals and YPRR remain in Receiving statistics below.'}</p></details>}
  {context&&<details className="receiving-route-adjustment"><summary>Route / coverage projection adjustment</summary><p>Recent usage: {num(forecast?.features?.targets_last3)} targets per game over the last 3 recorded games.{market?` ${player.team} market-implied points: ${num(market.points)} (${market.book}; market context, not an extra multiplier).`:''}</p><div className="table-scroll"><table><thead><tr><th>Stat</th><th>Core baseline</th><th>Current projection</th></tr></thead><tbody>{[['Targets','player_targets'],['Receptions','player_receptions'],['Receiving yards','player_reception_yds']].map(([label,key])=><tr key={key}><td>{label}</td><td>{num(forecast?.marketSamples?.[key]?.routeBaselineMean)}</td><td>{num(forecast?.marketSamples?.[key]?.mean)}</td></tr>)}</tbody></table></div>{context.rationale?.map((text:string)=><p key={text}>{text}</p>)}{forecast?.workloadContext&&<p>Current projections also include the disclosed teammate-return workload allocation; the route baseline precedes that allocation.</p>}</details>}
 </section>;
}
