'use client';
import {useEffect,useState} from 'react';
import {teamNames as names} from '../../../web/market-core.mjs';
import {researchHref} from '../../../web/research-links.mjs';
const teamNames:Record<string,string>=names;
export function normalizeTeam(team:string){return team==='LA'?'LAR':team==='WSH'?'WAS':Object.keys(teamNames).find(key=>teamNames[key]===team)||team}
export default function TeamMark({team,link=true,small=false,label=true}:{team:string,link?:boolean,small?:boolean,label?:boolean}){const code=normalizeTeam(team||''),[failed,setFailed]=useState(false),espn=code==='WAS'?'wsh':code.toLowerCase(),name=teamNames[code]||team||'Unknown team';useEffect(()=>setFailed(false),[code]);const content=<>{!failed&&code?<img src={'https://a.espncdn.com/i/teamlogos/nfl/500/'+espn+'.png'} alt={name+' logo'} width={small?22:42} height={small?22:42} loading="lazy" onError={()=>setFailed(true)}/>:null}{(label||failed)&&<span>{code}</span>}</>;return link?<a className={'team-mark'+(small?' small':'')} href={researchHref('teams',{team:code})} title={'View '+name+' statistics'} aria-label={'View '+name+' statistics'}>{content}</a>:<span className={'team-mark'+(small?' small':'')} title={name}>{content}</span>}
