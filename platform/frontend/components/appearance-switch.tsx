'use client';
import {useEffect,useState} from 'react';
import DensitySwitch from './density-switch';
import MotionSwitch from './motion-switch';
type Appearance='ember'|'glass'|'white';
export default function AppearanceSwitch(){const [appearance,setAppearance]=useState<Appearance>('ember');useEffect(()=>{try{const stored=localStorage.getItem('pns-appearance');if(stored==='glass'||stored==='ember'||stored==='white'){setAppearance(stored);document.documentElement.dataset.appearance=stored}}catch{}},[]);
 const choose=(value:Appearance)=>{setAppearance(value);document.documentElement.dataset.appearance=value;try{localStorage.setItem('pns-appearance',value)}catch{}};
 return <div className="display-controls"><MotionSwitch/><div className="appearance-switch" role="group" aria-label="Website appearance">{(['glass','ember','white'] as const).map(value=><button type="button" key={value} aria-pressed={appearance===value} title={value==='white'?'White glass with grey and teal waves':value==='ember'?'Warm charcoal and orange appearance':'Cool liquid glass appearance'} className={appearance===value?'active':''} onClick={()=>choose(value)}><span className={'appearance-dot '+value}/>{value==='white'?'White':value==='ember'?'Ember':'Glass'}</button>)}</div><DensitySwitch/></div>
}
