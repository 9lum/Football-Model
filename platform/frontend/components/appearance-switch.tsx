'use client';
import {useEffect,useState} from 'react';
type Appearance='ember'|'glass';
export default function AppearanceSwitch(){const [appearance,setAppearance]=useState<Appearance>('ember');useEffect(()=>{try{const stored=localStorage.getItem('pns-appearance');if(stored==='glass'||stored==='ember'){setAppearance(stored);document.documentElement.dataset.appearance=stored}}catch{}},[]);
 const choose=(value:Appearance)=>{setAppearance(value);document.documentElement.dataset.appearance=value;try{localStorage.setItem('pns-appearance',value)}catch{}};
 return <div className="appearance-switch" role="group" aria-label="Website appearance">{(['glass','ember'] as const).map(value=><button type="button" key={value} aria-pressed={appearance===value} title={value==='ember'?'Warm charcoal and orange appearance':'Cool liquid glass appearance'} className={appearance===value?'active':''} onClick={()=>choose(value)}><span className={'appearance-dot '+value}/>{value==='ember'?'Ember':'Glass'}</button>)}</div>
}
