'use client';
import {useEffect,useId,useState} from 'react';
import {normalizeZoom,zoomStyle,ZOOM_STORAGE_KEY} from '../../../web/display-zoom.mjs';
export default function ZoomControl(){
 const [zoom,setZoom]=useState(100),id=useId();
 function apply(value:any){const next=normalizeZoom(value),styles=zoomStyle(next);setZoom(next);document.documentElement.style.setProperty('--pns-zoom',styles.scale);document.documentElement.style.setProperty('--pns-viewport-height',styles.height)}
 useEffect(()=>{try{apply(localStorage.getItem(ZOOM_STORAGE_KEY))}catch{apply(100)}const sync=(e:StorageEvent)=>{if(e.key===ZOOM_STORAGE_KEY||e.key===null)apply(e.newValue)};window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync)},[]);
 function change(value:string){const next=normalizeZoom(value);apply(next);try{localStorage.setItem(ZOOM_STORAGE_KEY,String(next))}catch{}}
 return <div className="zoom-control"><label htmlFor={id}>Zoom</label><input id={id} type="range" min="100" max="200" step="1" value={zoom} aria-label="Website zoom" aria-valuetext={zoom+' percent'} onChange={e=>change(e.target.value)}/><output htmlFor={id}>{zoom}%</output></div>;
}
