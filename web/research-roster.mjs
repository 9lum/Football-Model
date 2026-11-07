import {teamNames} from './market-core.mjs';
const positions=['QB','RB','WR','TE'];
export const researchPositionLabel=p=>p==='RB'||p==='HB'?'HB':p;
const position=p=>p.position==='HB'?'RB':p.position;
export function injuryOrder(p){const h=p.health||{};if(h.scopeMismatch)return 0;if(h.ruledOut)return 3;return ({QUESTIONABLE:1,DOUBTFUL:2,OUT:3,IR:3,INACTIVE:3,SUSPENDED:3,PUP:3})[String(h.status||'').toUpperCase()]||0}
function usage(p){const key=position(p)==='QB'?'attempts':position(p)==='RB'?'carries':'targets',rows=(p.history||[]).filter(g=>g.team===p.team&&Number.isFinite(g[key])).slice(-4);if(rows.length)return rows.reduce((s,g)=>s+g[key]+(key==='carries'?(g.targets||0):0),0)/rows.length;if(p.previousStatTeam&&p.previousStatTeam!==p.team)return 0;return (p.basicStats?.perGame?.[key]||0)+(key==='carries'?(p.basicStats?.perGame?.targets||0):0)}
function depth(p){const r=p.roster;if(r?.fresh!==false&&Number.isFinite(r?.rank)&&r.rank>0)return r.rank;return p.expectedReplacement||r?.fresh!==false&&(r?.expectedStarter||r?.listedStarter)?1:99}
function depthOrder(a,b){return depth(a)-depth(b)||usage(b)-usage(a)||a.name.localeCompare(b.name)||String(a.playerId).localeCompare(String(b.playerId))}
export function groupResearchRoster(players,allPlayers=players){
 const pool=new Map();for(const p of [...allPlayers,...players])pool.set(p.playerId,p);
 const depthGroups=new Map();for(const p of pool.values()){const key=p.team+'|'+position(p);if(!depthGroups.has(key))depthGroups.set(key,[]);depthGroups.get(key).push(p)}
 const estimates=new Map();for(const rows of depthGroups.values())rows.sort(depthOrder).forEach((p,i)=>estimates.set(p.playerId,{rank:i+1,source:depth(p)<99?'Depth chart + observed usage':'Observed usage estimate'}));
 const teams=new Map();for(const p of players){if(!teams.has(p.team))teams.set(p.team,new Map());const groups=teams.get(p.team),pos=position(p);if(!groups.has(pos))groups.set(pos,[]);groups.get(pos).push({...p,researchDepth:estimates.get(p.playerId)})}
 return [...teams].sort(([a],[b])=>(teamNames[a]||a||'Unknown').localeCompare(teamNames[b]||b||'Unknown')).map(([team,groups])=>({team,name:teamNames[team]||team,positions:[...groups].sort(([a],[b])=>{const x=positions.indexOf(a),y=positions.indexOf(b);return (x<0?99:x)-(y<0?99:y)||a.localeCompare(b)}).map(([position,rows])=>({position,label:researchPositionLabel(position),players:rows.sort((a,b)=>injuryOrder(a)-injuryOrder(b)||a.researchDepth.rank-b.researchDepth.rank||a.name.localeCompare(b.name))}))}));
}
