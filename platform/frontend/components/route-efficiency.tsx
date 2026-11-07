'use client';
import {useEffect,useState} from 'react';
import {routeEfficiency} from '../../../web/route-research.mjs';
const BASE=process.env.NEXT_PUBLIC_DATA_BASE||'https://raw.githubusercontent.com/9lum/Football-Model/main/data';
let pending:Promise<any>|null=null,loadedAt=0;
function load(){if(!pending||Date.now()-loadedAt>300000){loadedAt=Date.now();pending=fetch(BASE+'/route-research.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null)}return pending}
export default function RouteEfficiency({player,season}:{player:any;season?:string}){
 const [snapshot,setSnapshot]=useState<any>(null);
 useEffect(()=>{let active=true;const update=()=>load().then(value=>{if(active)setSnapshot(value)});update();const timer=setInterval(update,300000);return()=>{active=false;clearInterval(timer)}},[]);
 if(!['WR','TE'].includes(player?.position))return null;
 const row=routeEfficiency(player,snapshot);
 const historical=season&&snapshot&&String(snapshot.season)!==String(season);
 const value=historical?null:row;
 return <div className="route-efficiency" aria-label="Yards per route run" style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,flexWrap:'wrap',padding:'10px 12px',margin:'10px 0',borderRadius:10,border:'1px solid color-mix(in srgb, var(--text, currentColor) 18%, transparent)',background:'color-mix(in srgb, currentColor 5%, transparent)'}} title="Receiving yards divided by actual routes from the same published snapshot. Season aggregate; not a last-3/6/9-game rate."><div><span style={{display:'block',fontSize:11,fontWeight:600,letterSpacing:'.02em'}}>Yards per route run <span className="muted">· YPRR</span></span><span className="small muted">{value?<>{value.season} season · {value.routes} routes · <a href={value.source} target="_blank" rel="noreferrer">Source {new Date(value.asOf).toLocaleDateString()}</a></>:historical?'Historical route counts unavailable':snapshot?'Published route counts unavailable':'Loading published route data…'}</span></div><strong style={{fontSize:23,lineHeight:1.15,fontVariantNumeric:'tabular-nums'}}>{value?value.yardsPerRouteRun.toFixed(2):'—'}</strong></div>
}
