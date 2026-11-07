'use client';
import {useEffect,useId,useState} from 'react';
import {normalizeZoom,zoomStyle,ZOOM_STORAGE_KEY,ZOOM_LEVELS} from '../../../web/display-zoom.mjs';
export default function ZoomControl(){
 const [zoom,setZoom]=useState(100),id=useId();
 function apply(value:any){const next=normalizeZoom(value),styles=zoomStyle(next);setZoom(next);document.documentElement.style.setProperty('--pns-zoom',styles.scale);document.documentElement.style.setProperty('--pns-viewport-height',styles.height)}
 useEffect(()=>{try{apply(localStorage.getItem(ZOOM_STORAGE_KEY))}catch{apply(100)}const sync=(e:StorageEvent)=>{if(e.key===ZOOM_STORAGE_KEY||e.key===null)apply(e.newValue)};window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync)},[]);
 function change(value:string){const next=normalizeZoom(value);apply(next);try{localStorage.setItem(ZOOM_STORAGE_KEY,String(next))}catch{}}
 return <div className="zoom-control"><label htmlFor={id}>Zoom</label><select id={id} value={zoom} aria-label="Website zoom" onChange={e=>change(e.target.value)}>{ZOOM_LEVELS.map(value=><option key={value} value={value}>{value===0?'0% — Reset':value+'%'}</option>)}</select></div>;
}
