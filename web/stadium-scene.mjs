const finite=v=>typeof v==='number'&&Number.isFinite(v);
export const normalizeBearing=v=>((v%360)+360)%360;
// Meteorological wind direction is FROM; the vector below points TO.
// Positive x is toward End B. Positive y is the lower touchline in the field view.
export function fieldWind(hour,bearing=0,closed=false){
 if(closed)return {from:null,to:null,alongKph:0,crossKph:0,speedKph:0,sheltered:true};
 if(!finite(hour?.windDirection)||!finite(hour?.windKph)||hour.windKph<0||!finite(bearing))return null;
 const from=normalizeBearing(hour.windDirection),to=normalizeBearing(from+180),angle=(to-normalizeBearing(bearing))*Math.PI/180;
 return {from,to,speedKph:hour.windKph,alongKph:hour.windKph*Math.cos(angle),crossKph:hour.windKph*Math.sin(angle),sheltered:false};
}
export function kickWind(wind,end='B'){
 if(!wind)return null;const along=wind.alongKph*(end==='B'?1:-1);
 return {headwindKph:Math.max(0,-along),tailwindKph:Math.max(0,along),crosswindKph:Math.abs(wind.crossKph),crossDirection:wind.crossKph>.05?'lower':wind.crossKph<-.05?'upper':'none'};
}
export function projectedSky(hour){
 if(!hour)return {kind:'unknown',precipitation:'none',night:false,clouds:0};
 const code=hour.weatherCode,night=hour.isDay===0,known=finite(code),clouds=finite(hour.cloudPct)?Math.max(0,Math.min(100,hour.cloudPct))/100:known&&code>1?.7:0;
 let precipitation='none';
 if((finite(hour.snowfallCm)&&hour.snowfallCm>0)||(known&&((code>=71&&code<=77)||(code>=85&&code<=86))))precipitation='snow';
 else if((finite(hour.precipitationMm)&&hour.precipitationMm>0)||(known&&((code>=51&&code<=67)||(code>=80&&code<=82)||code>=95)))precipitation='rain';
 return {kind:!known?'unknown':code>=95?'storm':code>=45&&code<=48?'fog':precipitation!=='none'?precipitation:clouds>.75?'cloudy':clouds>.25?'partly-cloudy':night?'clear-night':'sun',precipitation,night,clouds};
}
