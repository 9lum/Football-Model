'use client';
import {useEffect,useMemo,useState} from 'react';
import {mergePlayerGames} from '../../../web/player-game-data.mjs';
const BASE=process.env.NEXT_PUBLIC_DATA_BASE||'https://raw.githubusercontent.com/9lum/Football-Model/main/data';
const cache=new Map<string,{time:number,value:Promise<any>}>();
function read(name:string){const old=cache.get(name);if(old&&Date.now()-old.time<60000)return old.value;const value=fetch(BASE+'/'+name+'.json?t='+Math.floor(Date.now()/60000),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(name+': '+r.status);return r.json()});cache.set(name,{time:Date.now(),value});return value;}
export function usePlayerGames(player:any,focusGameId?:string){
 const [state,setState]=useState<any>({}),[archives,setArchives]=useState<Record<string,any>>({});const id=player?.playerId;
 useEffect(()=>{if(!/^[A-Za-z0-9_-]{1,80}$/.test(id||''))return;let active=true;const update=async()=>{const [payload,recent]=await Promise.all([read('player-research/'+id).catch(()=>null),read('recent-player-actuals').catch(()=>null)]);if(active)setState({id,payload,recent})};void update();const timer=setInterval(update,60000);return()=>{active=false;clearInterval(timer)}},[id]);
 const payload=state.id===id?state.payload:null,recent=state.id===id?state.recent:null,games=useMemo(()=>mergePlayerGames(player?.history||[],payload,[...(player?.recentActualRows||[]),...(recent?.rows||[]).filter((r:any)=>r.playerId===id)]),[player?.history,player?.recentActualRows,payload,recent,id]);
 const key=[...games.slice(-12).map((g:any)=>g.gameId),focusGameId].filter(Boolean).join('|');
 useEffect(()=>{let active=true;void read('matchup-research-index').then(async index=>{const known=new Set((index.games||[]).map((g:any)=>g.gameId)),ids=key.split('|').filter(g=>known.has(g)&&/^\d{4}_\d{2}_[A-Z]+_[A-Z]+$/.test(g));const values=await Promise.all(ids.map(g=>read('matchup-research/'+g).then(value=>[g,value]).catch(()=>null)));if(active)setArchives(Object.fromEntries(values.filter(Boolean) as any))}).catch(()=>{});return()=>{active=false}},[id,key]);
 return {games,payload,recent,archives};
}
