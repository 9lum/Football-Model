// Keep public-page timestamps and provenance separate; prefer primary API offers.
export function mergeTouchdownSnapshots(primary,publicSnapshot){
 const data=(primary?.data||[]).map(e=>({...e,bookmakers:(e.bookmakers||[]).map(b=>({...b,markets:(b.markets||[]).map(m=>({...m,outcomes:[...(m.outcomes||[])]}))}))}));
 for(const e of publicSnapshot?.data||[]){let event=data.find(x=>x.home_team===e.home_team&&x.away_team===e.away_team&&Date.parse(x.commence_time)===Date.parse(e.commence_time));if(!event){data.push(e);continue}for(const b of e.bookmakers||[]){let book=event.bookmakers.find(x=>x.key===b.key);if(!book){event.bookmakers.push(b);continue}for(const m of b.markets||[]){const old=book.markets.find(x=>x.key===m.key);if(!old){book.markets.push(m);continue}const missing=(m.outcomes||[]).filter(o=>!old.outcomes.some(p=>String(p.description||p.name).toLowerCase()===String(o.description||o.name).toLowerCase()));if(missing.length)book.markets.push({...m,outcomes:missing})}}}
 return {...primary,data,publicSource:publicSnapshot?.source};
}
