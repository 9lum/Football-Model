const valid=x=>typeof x==='number'&&Number.isFinite(x);
export function selectGames(games,season,window='season'){const rows=games.filter(g=>Number(g.season)===Number(season)).sort((a,b)=>String(a.kickoff||'').localeCompare(String(b.kickoff||''))||a.week-b.week);return window==='season'?rows:rows.slice(-Number(window));}
export function playerStatSummary(games,position){
 const result=[];const total=(path)=>{const vals=games.map(g=>path.split('.').reduce((v,k)=>v?.[k],g)).filter(valid);return vals.length?vals.reduce((a,b)=>a+b,0):null};
 const add=(label,value,unit='')=>{if(valid(value))result.push({label,value,unit})};
 const sum=(label,key)=>add(label,total('basic.'+key));
 const ratio=(label,n,d,m=1,unit='')=>{const rows=games.map(g=>[g.basic?.[n],g.basic?.[d]]).filter(([a,b])=>valid(a)&&valid(b));const den=rows.reduce((s,r)=>s+r[1],0);if(den>0)add(label,m*rows.reduce((s,r)=>s+r[0],0)/den,unit)};
 const weighted=(label,source,key,weight,unit='')=>{const rows=games.map(g=>g.advanced?.[source]).filter(r=>valid(r?.[key])&&valid(r?.[weight])&&r[weight]>0);const den=rows.reduce((s,r)=>s+r[weight],0);if(den)add(label,rows.reduce((s,r)=>s+r[key]*r[weight],0)/den,unit)};
 const advsum=(label,source,key)=>add(label,total('advanced.'+source+'.'+key));
 if(position==='QB'){
  for(const [label,key] of [['Pass yards','passing_yards'],['Pass TD','passing_tds'],['Interceptions','passing_interceptions'],['Attempts','attempts'],['Completions','completions'],['Sacks taken','sacks_suffered'],['Carries','carries'],['Rush yards','rushing_yards'],['Rush TD','rushing_tds']])sum(label,key);
  ratio('Completion rate','completions','attempts',100,'%');ratio('Yards / attempt','passing_yards','attempts');weighted('Time to throw','ngs_passing','avg_time_to_throw','attempts','s');weighted('CPOE','ngs_passing','completion_percentage_above_expectation','attempts','pp');advsum('Pressured dropbacks','pfr_pass','times_pressured');advsum('Bad throws','pfr_pass','passing_bad_throws');
 }else if(['RB','HB','FB'].includes(position)){
  for(const [label,key] of [['Carries','carries'],['Rush yards','rushing_yards'],['Rush TD','rushing_tds'],['Targets','targets'],['Receptions','receptions'],['Receiving yards','receiving_yards'],['Receiving TD','receiving_tds']])sum(label,key);
  ratio('Yards / carry','rushing_yards','carries');weighted('Rush yards over expected / carry','ngs_rushing','rush_yards_over_expected_per_att','rush_attempts');advsum('Yards after contact','pfr_rush','rushing_yards_after_contact');advsum('Broken tackles','pfr_rush','rushing_broken_tackles');
 }else{
  for(const [label,key] of [['Targets','targets'],['Receptions','receptions'],['Receiving yards','receiving_yards'],['Receiving TD','receiving_tds'],['Receiving first downs','receiving_first_downs']])sum(label,key);
  ratio('Catch rate','receptions','targets',100,'%');ratio('Yards / reception','receiving_yards','receptions');ratio('aDOT','receiving_air_yards','targets');ratio('YAC / reception','receiving_yards_after_catch','receptions');weighted('Separation','ngs_receiving','avg_separation','targets','yd');weighted('YAC over expected','ngs_receiving','avg_yac_above_expectation','receptions','yd');advsum('Drops','pfr_rec','receiving_drop');
 }
 return result;
}
export function modelInputSummary(features,position){const common=[['offense_pct_last3','Offensive snap share · last 3'],['usage_trend','Usage trend'],['days_since_game','Days since last game']];const fields=position==='QB'?[['attempts_last3','Pass attempts · last 3'],['pass_ypa','Passing yards / attempt']]:position==='RB'?[['carries_last3','Carries · last 3'],['targets_last3','Targets · last 3'],['rush_ypc','Rushing yards / carry']]:[['targets_last3','Targets · last 3'],['adot_last6','aDOT · last 6'],['target_share_last6','Target share · last 6']];return Object.fromEntries([...fields,...common].filter(([key])=>valid(features?.[key])).map(([key,label])=>[label,features[key]]));}
