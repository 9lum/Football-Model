'use client';
import {useEffect,useState} from 'react';
import {routeEfficiency} from '../../../web/route-research.mjs';
const BASE=process.env.NEXT_PUBLIC_DATA_BASE||'https://raw.githubusercontent.com/9lum/Football-Model/main/data';
let pending:Promise<any>|null=null,loadedAt=0;
function load(){if(!pending||Date.now()-loadedAt>300000){loadedAt=Date.now();pending=fetch(BASE+'/route-research.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null)}return pending}
export default function RouteEfficiency({player,season,statCell=false}:{player:any;season?:string;statCell?:boolean}){
 const [snapshot,setSnapshot]=useState<any>(null);
 useEffect(()=>{let active=true;const update=()=>load().then(value=>{if(active)setSnapshot(value)});update();const timer=setInterval(update,300000);return()=>{active=false;clearInterval(timer)}},[]);
 if(!['WR','TE'].includes(player?.position))return null;
 const row=routeEfficiency(player,snapshot);
 const historical=season&&snapshot&&String(snapshot.season)!==String(season);
 const value=historical?null:row;
 if(statCell)return <div className="route-efficiency" title="Receiving yards divided by actual routes from the same published season snapshot; not a last-3/6/9-game rate."><dt>Yards per route run · YPRR</dt><dd>{value?value.yardsPerRouteRun.toFixed(2):'—'}</dd><small className="muted">{value?<>{value.season} season · {value.routes} routes · <a href={value.source} target="_blank" rel="noreferrer">Source {new Date(value.asOf).toLocaleDateString()}</a></>:historical?'Historical routes unavailable':snapshot?'Route counts unavailable':'Loading routes…'}</small></div>;
 return <section className="route-receiving-statistics" aria-label="Receiving statistics" style={{marginTop:16,paddingTop:12,borderTop:'1px solid color-mix(in srgb, currentColor 15%, transparent)'}}><h4 style={{margin:'0 0 8px',fontSize:13}}>Receiving statistics</h4><dl className="research-stat-grid" style={{margin:0}}><div className="route-efficiency" title="Season receiving yards divided by actual routes; not a last-3/6/9-game rate."><dt>Yards per route run · YPRR</dt><dd>{value?value.yardsPerRouteRun.toFixed(2):'—'}</dd><small className="muted">{value?<>{value.season} season · {value.routes} routes · <a href={value.source} target="_blank" rel="noreferrer">Source {new Date(value.asOf).toLocaleDateString()}</a></>:historical?'Historical route counts unavailable':snapshot?'Route counts unavailable':'Loading routes…'}</small></div></dl></section>
}
