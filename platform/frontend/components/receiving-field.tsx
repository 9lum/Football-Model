'use client';
import {useState} from 'react';
import FieldSurface from './field-surface';
import './receiving-field.css';
import {impliedTeamPoints,matchGameMarket} from '../../../web/game-markets.mjs';
import {teamNames} from '../../../web/market-core.mjs';
const pct=(n:any)=>Number.isFinite(n)?Math.round(n*100)+'%':'—';
const num=(n:any,d=1)=>Number.isFinite(n)?Number(n).toFixed(d):'—';
const depths=['short','intermediate','deep'],areas=['left','middle','right'];
const palette:Record<string,string>={short:'#55cbb0',intermediate:'#7bb5ff',deep:'#c4a0f2'};
export default function ReceivingField({player,forecast,research,events=[]}:any){
 const [period,setPeriod]=useState('last6'),[zoneSelection,setSelection]=useState(''),[tilted,setTilted]=useState(true),[paths,setPaths]=useState(false);
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
    <FieldSurface player={player} zones={zones} selection={selection} onSelect={setSelection} depth={tilted} paths={paths} qb={qb}/>

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
