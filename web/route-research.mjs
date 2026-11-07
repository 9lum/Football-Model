const canonical=value=>String(value||'').toLowerCase().replace(/[^a-z0-9]/g,'');
export function routeEfficiency(player,snapshot,now=Date.now()){
 if(!['WR','TE'].includes(player?.position))return null;
 const season=new Date(now).getUTCFullYear()-(new Date(now).getUTCMonth()<2?1:0);
 const rows=(snapshot?.players||[]).filter(r=>r.position===player.position&&r.team===player.team&&r.season===season&&canonical(r.slug)===canonical(player.name||player.player||player.player_display_name));
 if(rows.length!==1)return null;const r=rows[0],age=now-Date.parse(r.asOf);
 if(!Number.isFinite(age)||age<0||age>7*86400000||!Number.isFinite(r.routes)||r.routes<=0||!Number.isFinite(r.receivingYards))return null;
 return {...r,yardsPerRouteRun:r.receivingYards/r.routes};
}
