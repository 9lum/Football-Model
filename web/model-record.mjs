export const recordMarkets={total:'Game over / under',moneyline:'Moneylines',touchdown:'Touchdown scorers'};
export function filterRecord(rows=[],season='all',week='all',market='all'){
 return rows.filter(r=>(season==='all'||String(r.season)===String(season))&&(week==='all'||String(r.week)===String(week))&&(market==='all'||r.market===market));
}
export function summarizeRecord(rows=[]){
 const summary={wins:0,losses:0,pushes:0,pending:0,ungraded:0,hitRate:null};
 for(const r of rows){const key={win:'wins',loss:'losses',push:'pushes',pending:'pending',ungraded:'ungraded'}[r.status];if(key)summary[key]++;}
 const settled=summary.wins+summary.losses;summary.hitRate=settled?summary.wins/settled:null;return summary;
}
