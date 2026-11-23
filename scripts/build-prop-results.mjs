import fs from 'node:fs';
import path from 'node:path';
import {buildPropResults} from '../web/prop-results.mjs';
const root=process.env.PROP_RESULTS_DATA||'data',read=n=>JSON.parse(fs.readFileSync(path.join(root,n+'.json'),'utf8'));
const index=read('matchup-research-index'),actuals=read('recent-player-actuals');
const latest=Math.max(...(index.games||[]).map(g=>Number(g.gameId.split('_')[0])*100+Number(g.gameId.split('_')[1])));
const archives=(index.games||[]).filter(g=>Number(g.gameId.split('_')[0])*100+Number(g.gameId.split('_')[1])>=latest-3).flatMap(g=>{try{return[read('matchup-research/'+g.gameId)]}catch{return[]}});
const output={...buildPropResults(archives,actuals),generatedAt:new Date().toISOString(),actualsObservedAt:actuals.generatedAt};
const directory=path.join(root,'prop-results');fs.mkdirSync(directory,{recursive:true});const weeks=new Map();
for(const group of output.groups){const [season,week]=group.first.gameId.split('_');const key=season+'_'+week;if(!weeks.has(key))weeks.set(key,[]);weeks.get(key).push(group)}
const indexRows=[];
for(const [key,groups] of weeks){const value={...output,groups};fs.writeFileSync(path.join(directory,key+'.json'),JSON.stringify(value));indexRows.push({key,players:groups.length,completed:groups.filter(g=>g.first.completed).length})}
fs.writeFileSync(path.join(root,'prop-results.json'),JSON.stringify({generatedAt:output.generatedAt,weeks:indexRows,scope:output.scope}));
console.log(JSON.stringify({playerGameCards:output.groups.length,weeks:indexRows}));
