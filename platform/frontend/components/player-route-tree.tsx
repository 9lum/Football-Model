'use client';
import {useEffect,useState} from 'react';
import RouteExperiment from './route-experiment';
const BASE=process.env.NEXT_PUBLIC_DATA_BASE||'https://raw.githubusercontent.com/9lum/Football-Model/main/data';
let cached:{at:number,value:Promise<any>}|null=null;
function read(){if(cached&&Date.now()-cached.at<300000)return cached.value;const value=fetch(BASE+'/route-experiment.json?t='+Math.floor(Date.now()/300000),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Charting unavailable');return r.json()}).catch(e=>{cached=null;throw e});cached={at:Date.now(),value};return value;}
export default function PlayerRouteTree({player}:any){
 const [snapshot,setSnapshot]=useState<any>(null),[error,setError]=useState(false),[retry,setRetry]=useState(0);
 const relevant=['QB','WR','TE','RB','HB','FB'].includes(player?.position);
 useEffect(()=>{if(!relevant)return;let active=true;const load=()=>read().then(v=>{if(active){setSnapshot(v);setError(false)}}).catch(()=>{if(active)setError(true)});void load();const timer=setInterval(load,300000);return()=>{active=false;clearInterval(timer)}},[relevant,retry]);
 if(!relevant)return null;
 if(error&&!snapshot)return <section className="receiving-field-panel"><h3>Route concepts & tendencies</h3><p className="small muted">Public charting is temporarily unavailable.</p><button onClick={()=>{setError(false);setRetry(v=>v+1)}}>Retry chart</button></section>;
 return <RouteExperiment key={player.playerId} players={[player]} embeddedPlayer={player} snapshot={snapshot}/>;
}
