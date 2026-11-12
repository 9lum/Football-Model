/** Keep the current NFL week as the default; expose only available TD archives. */
export function touchdownWeekView(report={},view={},selectedKey=''){
 const season=Number(view.season??report.season),week=Number(view.week??report.week),active=season*100+week;
 if(!Number.isInteger(season)||season<2000||!Number.isInteger(week)||week<1)return {season:null,week:null,key:'',weeks:[],games:[],historical:false};
 const fixtures=new Map((view.games||[]).map(g=>[g.game_id,g])),groups=new Map(),activeKey=season+'-'+week;
 groups.set(activeKey,{key:activeKey,season,week,games:[]});
 const seen=new Set();for(const g of report.games||[]){if(seen.has(g.gameId))continue;seen.add(g.gameId);const fixture=fixtures.get(g.gameId),id=/^(\d{4})_(\d{2})_[A-Z]+_[A-Z]+$/.exec(g.gameId||''),s=Number(fixture?.season??id?.[1]),w=Number(fixture?.week??id?.[2]);
 if(!Number.isInteger(s)||s<2000||!Number.isInteger(w)||w<1||w>22||s*100+w>active)continue;
 const key=s+'-'+w;if(!groups.has(key))groups.set(key,{key,season:s,week:w,games:[]});groups.get(key).games.push(g);}
 const selected=groups.get(selectedKey)||groups.get(activeKey),weeks=[...groups.values()].sort((a,b)=>b.season-a.season||b.week-a.week).map(({games,...w})=>({...w,current:w.key===activeKey}));
 return {...selected,weeks,historical:selected.key!==activeKey};
}
