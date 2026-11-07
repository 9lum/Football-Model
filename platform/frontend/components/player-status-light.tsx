'use client';
import {createContext,useContext,useId,useMemo,useState} from 'react';
import {createPortal} from 'react-dom';
import {playerHealthIndicator} from '../../../web/player-health.mjs';
const HealthContext=createContext<Map<string,any>|null>(null);
export function PlayerHealthProvider({players,children}:any){const health=useMemo(()=>new Map<string,any>((players||[]).map((p:any)=>[p.playerId,p.health||null])),[players]);return <HealthContext.Provider value={health}>{children}</HealthContext.Provider>}
export default function PlayerStatusLight({player,embedded=false}:any){
 const registry=useContext(HealthContext),id=useId(),[anchor,setAnchor]=useState<{left:number;top:number}|null>(null),health=registry?.has(player?.playerId)?registry.get(player.playerId):player?.health,status=playerHealthIndicator(health),label=(player?.name||player?.player||'Player')+': '+status.label;
 function show(e:any){const r=e.currentTarget.getBoundingClientRect();setAnchor({left:Math.max(8,Math.min(r.left,window.innerWidth-248)),top:Math.max(8,Math.min(r.bottom+9,window.innerHeight-110))})}
 return <><span className={'player-status-light status-'+status.tone} role="img" aria-label={embedded?status.label:label} aria-describedby={anchor?id:undefined} tabIndex={embedded?undefined:0} onMouseEnter={show} onMouseLeave={()=>setAnchor(null)} onFocus={show} onBlur={()=>setAnchor(null)} onKeyDown={e=>{if(e.key==='Escape')setAnchor(null)}}><span aria-hidden="true"/></span>{anchor&&createPortal(<div id={id} className="player-status-tooltip" role="tooltip" style={{left:anchor.left,top:anchor.top}}><strong>{status.label}</strong><span>{status.detail}</span></div>,document.body)}</>;
}
export function PlayerStatusLegend(){return <details className="player-status-key"><summary>Status lights</summary><div>{[['green','Healthy'],['yellow','Questionable'],['red','Doubtful / out'],['unknown','Unconfirmed']].map(([tone,label])=><span key={tone}><i className={'player-status-light status-'+tone} aria-hidden="true"><span/></i>{label}</span>)}</div></details>}
