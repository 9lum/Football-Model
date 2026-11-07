export const finite=v=>typeof v==='number'&&Number.isFinite(v);
export const mph=v=>finite(v)?v/1.609344:null;
export function weatherExposure(game,assumeClosed=false){return game?.roofType==='indoor'||(game?.roofType==='retractable'&&assumeClosed)?'indoor':'outdoor'}
export function weatherRisk(hour,exposure='outdoor'){
 if(exposure==='indoor')return {label:'Climate controlled',tone:'neutral',reasons:['Outdoor wind and precipitation are shielded by the roof.']};
 if(!hour||![hour.windKph,hour.gustKph,hour.precipitationMm,hour.snowfallCm,hour.temperatureC].every(finite))return {label:'Incomplete forecast',tone:'neutral',reasons:['Missing weather fields prevent a complete impact assessment.']};
 let score=0;const reasons=[];
 if(mph(hour.windKph)>=20||mph(hour.gustKph)>=30){score=2;reasons.push('Strong wind/gusts: deeper throws and long field goals warrant extra scrutiny.')}else if(mph(hour.windKph)>=12||mph(hour.gustKph)>=20){score=1;reasons.push('Breezy: deep-ball placement and kicking can be more variable.')}
 if(hour.precipitationMm>=2.5||hour.snowfallCm>=.5){score=Math.max(score,2);reasons.push('Heavier precipitation could affect footing, grip and ball handling.')}else if(hour.precipitationMm>=.2||hour.snowfallCm>0){score=Math.max(score,1);reasons.push('Wet conditions may affect grip and footing; amount matters more than rain probability alone.')}
 if(hour.temperatureC<=0||hour.temperatureC>=30){score=Math.max(score,1);reasons.push(hour.temperatureC<=0?'Freezing temperatures can affect handling and kicking; surface treatment matters.':'Heat can affect endurance and rotation; hydration and depth matter.')}
 if(hour.weatherCode>=95){score=2;reasons.push('Thunderstorm forecast: monitor official venue alerts and possible delays.')}
 if(finite(hour.visibilityM)&&hour.visibilityM<1000){score=Math.max(score,1);reasons.push('Low visibility could complicate downfield tracking.')}
 return {label:score===2?'Elevated weather risk':score===1?'Monitor conditions':'Limited weather pressure',tone:score===2?'warn':'neutral',reasons:reasons.length?reasons:['No major wind, precipitation or temperature trigger in this hour.']};
}
export function teamWeatherContext(team,hour,exposure,profile){
 const totals=profile?.offense?.totals||{},attempts=totals.attempts,carries=totals.carries,share=finite(attempts)&&finite(carries)&&attempts+carries>0?attempts/(attempts+carries):null;
 const perGame=profile?.offense?.perGame||{},yardage=finite(perGame.passing_yards)&&finite(perGame.rushing_yards)?` Recorded season baseline: ${perGame.passing_yards.toFixed(0)} passing / ${perGame.rushing_yards.toFixed(0)} rushing yards per game.`:'';
 const baseline=share===null?`${team}: no matched offensive tendency snapshot.`:`${team} has used pass attempts on ${(100*share).toFixed(0)}% of recorded pass attempts plus carries this season (sacks excluded).${yardage}`;
 if(exposure==='indoor')return [baseline,'With the roof closed, outdoor wind/rain should not drive a passing-yard downgrade or a rushing-volume boost. Matchup, personnel and score remain the main inputs.'];
 if(!hour||!finite(hour.windKph)||!finite(hour.gustKph)||!finite(hour.precipitationMm))return [baseline,'A complete forecast is unavailable; no weather-driven stat or game-plan conclusion is supported yet.'];
 const windy=mph(hour.windKph)>=15||mph(hour.gustKph)>=25,wet=hour.precipitationMm>=.2||hour.snowfallCm>0;
 return [baseline,windy?`Wind makes ${team}'s longer throws and long field goals more sensitive to conditions. Shorter passes, screens and ground-game alternatives may become more attractive; a pass-heavy baseline increases exposure, but does not establish a yardage deduction.`:wet?`Wet conditions could make ${team}'s ball security, footing and catch execution more important. Rushing does not automatically become efficient in rain; opponent fronts and the playing surface still matter.`:`The forecast offers little reason by itself to change ${team}'s passing/rushing split. Use the opponent matchup and player roles to assess the stat line.`,windy&&wet?'Wind and wet conditions together warrant reviewing deep receiving-yard and kicking markets close to kickoff. These are scenario considerations, not a measured percentage change.':'Weather effects are contextual; this panel does not apply an unvalidated stat-line multiplier.'];
}
export function weatherDescription(code){if(!finite(code))return 'Forecast pending';if(code===0)return 'Clear';if(code<=3)return 'Cloud cover';if(code<=48)return 'Fog';if(code<=57)return 'Drizzle';if(code<=67)return 'Rain';if(code<=77)return 'Snow';if(code<=82)return 'Rain showers';if(code<=86)return 'Snow showers';return 'Thunderstorms'}
