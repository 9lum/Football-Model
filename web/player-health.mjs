export function playerHealthIndicator(health){
 const status=String(health?.status||'').toUpperCase();
 if(!health||health.scopeMismatch)return {tone:'unknown',label:'Unconfirmed',detail:'Current injury status is missing, stale or outside this game’s report.'};
 if(health.ruledOut||['OUT','IR','INACTIVE','PUP','NFI','SUSPENDED'].includes(status))return {tone:'red',label:'Out',detail:health.label||'Unavailable or ruled out'};
 if(status==='DOUBTFUL')return {tone:'red',label:'Doubtful',detail:'Doubtful designation; this does not itself confirm an absence.'};
 if(status==='QUESTIONABLE')return {tone:'yellow',label:'Questionable',detail:'Questionable designation; participation remains uncertain.'};
 if(['ACTIVE','HEALTHY','AVAILABLE','CLEARED'].includes(status))return {tone:'green',label:'Healthy',detail:'Current source lists the player active or cleared. This is not a guarantee of participation.'};
 return {tone:'unknown',label:'Unconfirmed',detail:status==='NOT_LISTED'?'No injury designation reported; active status is not confirmed.':health.label||'No confirmed current injury designation.'};
}
