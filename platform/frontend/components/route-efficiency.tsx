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
 if(season&&String(snapshot?.season)!==String(season))return <p className="small muted">YPRR · Historical route counts unavailable</p>;
 return <p className="route-efficiency small muted" title="Yards per route run uses actual receiving routes, not offensive snaps. Current season aggregate; not a last-3/6/9-game rate."><strong>YPRR {row?row.yardsPerRouteRun.toFixed(2):'—'}</strong>{row?<> · {row.routes} routes · {row.season} season <a href={row.source} target="_blank" rel="noreferrer">· Source {new Date(row.asOf).toLocaleDateString()}</a></>: ' · Published route counts unavailable'}</p>
}
