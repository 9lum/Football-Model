/** Rank each offense independently so one team's scorers cannot crowd out its opponent. */
export function touchdownTeamPicks(game,{position='',search=''}={}){
 const query=search.trim().toLowerCase();
 const pool=game.players?.length?game.players:game.candidates||[];
 return [game.awayTeam,game.homeTeam].filter(Boolean).map(team=>{
  const seen=new Set();
  const players=pool.filter(p=>{
   if(p.team!==team||!Number.isFinite(p.probability)||p.unavailable||p.health?.ruledOut||['OUT','IR','PUP','NFI','INACTIVE','SUSPENDED'].includes(String(p.health?.status||'').toUpperCase()))return false;
   if(position&&p.position!==position)return false;
   if(query&&![p.name,p.team].join(' ').toLowerCase().includes(query))return false;
   if(seen.has(p.playerId))return false;
   seen.add(p.playerId);return true;
  }).sort((a,b)=>b.probability-a.probability).slice(0,3).map((p,i)=>({...p,risk:i===0?'Team leader · highest estimated probability':'Top team scoring probability'}));
  return {team,players};
 });
}
