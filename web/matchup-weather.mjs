import {finite,mph,weatherExposure,teamWeatherContext} from './weather-research.mjs';
const usable=w=>w?.status==='ok'&&['temperatureC','windKph','gustKph','precipitationMm','precipitationProbability'].some(k=>finite(w[k]));
const time=w=>Date.parse(w?.retrievedAt||w?.observedAt)||0;
export function matchupWeather(game,stadium,basic,archived,reported,now=Date.now()){
 const id=game?.game_id||game?.gameId,kickoff=Date.parse(game?.kickoff),finished=game?.completed===true;
 const scoped=w=>w&&(!w.gameId||w.gameId===id)&&(!w.kickoff||Math.abs(Date.parse(w.kickoff)-kickoff)<3600000);
 const saved=scoped(archived)&&usable(archived)?{...archived,kind:'saved_pregame_forecast'}:null;
 if(finished&&saved)return saved;
 let stadiumForecast=null;if(scoped(stadium)&&['ok','archived'].includes(stadium.status)){
  const h=stadium.kickoffForecast||(stadium.hours||[]).find(h=>Math.abs(Date.parse(h.time)-kickoff)<=1800000);
  if(h)stadiumForecast={...h,status:'ok',gameId:id,kickoff:game.kickoff,provider:stadium.provider,source:stadium.source,retrievedAt:stadium.retrievedAt,forecastTime:h.time,exposure:weatherExposure(stadium),roofType:stadium.roofType,kind:'retained_hourly_forecast'};
 }
 const forecasts=[stadiumForecast,scoped(basic)?basic:null,saved].filter(usable).sort((a,b)=>time(b)-time(a));
 const report=scoped(reported)&&usable(reported)&&time(reported)<=now&&now-time(reported)<=15*60000?{...reported,exposure:stadium?weatherExposure(stadium):['dome','closed'].includes(game?.roof)?'indoor':'outdoor_or_unknown',roofType:stadium?.roofType}:null;
 if(!finished&&kickoff<=now&&report)return report;
 return forecasts[0]||report||{status:'unavailable',gameId:id,reason:'No verified game-specific weather is available. Weather-driven adjustments are not supported.'};
}
export function matchupWeatherImplications(game,weather,teamProfiles=[],forecasts=[]){
 const code=t=>({LA:'LAR',WSH:'WAS',JAC:'JAX'})[t]||t;
 const teams=[game?.away_team||game?.awayTeam,game?.home_team||game?.homeTeam].filter(Boolean).map(code);
 return teams.map(team=>{
  const eligible=forecasts.filter(f=>f.gameId===(game.game_id||game.gameId)&&f.team===team&&!f.unavailable&&f.likelyToPlay!==false);
  const players=eligible.filter(f=>f.position==='QB').slice(0,1).concat(eligible.filter(f=>['WR','TE'].includes(f.position)).sort((a,b)=>(b.features?.targets_last3||0)-(a.features?.targets_last3||0)).slice(0,1));
  const names=players.map(p=>p.name).filter(Boolean),profile=teamProfiles.find(p=>p.team===team),baseline=teamWeatherContext(team,weather,weather?.exposure,profile)[0];
  if(weather?.status!=='ok')return {team,names,baseline,summary:'Weather data is unavailable; no weather-driven change to passing, rushing or kicking is supported.'};
  if(weather.exposure==='indoor')return {team,names,baseline,summary:'A fixed or confirmed closed roof shields the field from outdoor wind and rain; personnel and opponent matchups remain the main factors.'};
  const notes=[];
  if(finite(weather.windKph)&&mph(weather.windKph)>=15||finite(weather.gustKph)&&mph(weather.gustKph)>=25)notes.push('Wind could make deep throws and long field goals less reliable; shorter routes, screens and rushing alternatives may become more attractive.');
  else if(finite(weather.windKph)||finite(weather.gustKph))notes.push('Reported wind measurements do not show the strong-wind trigger; that alone does not justify a passing-yard downgrade.');
  if(finite(weather.precipitationMm)&&weather.precipitationMm>=.2||finite(weather.snowfallCm)&&weather.snowfallCm>0)notes.push('Wet or snowy conditions may affect grip, footing and exchanges; they do not guarantee extra rushing volume.');
  if(finite(weather.temperatureC)&&weather.temperatureC<=0)notes.push('Freezing temperatures add handling and kicking considerations.');
  if(!finite(weather.precipitationMm))notes.push('Precipitation amount is unverified, so a rain-based projection adjustment is not supported.');
  if(!notes.length)notes.push('The available measurements offer no standalone reason to alter the game plan; missing measurements are not treated as calm or dry.');
  return {team,names,baseline,summary:notes.slice(0,2).join(' ')};
 });
}
export function matchupWeatherStale(game,weather,now=Date.now()){
 const collected=time(weather),age=now-collected,kickoff=Date.parse(game?.kickoff);
 if(weather?.status!=='ok'||!collected||age<0)return true;
 if(kickoff>now)return kickoff-now<=15*60000?collected<kickoff-20*60000:age>90*60000;
 return weather.kind==='reported_game_conditions'&&age>15*60000;
}
