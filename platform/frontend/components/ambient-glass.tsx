'use client';
import {useEffect,useRef} from 'react';
export default function AmbientGlass(){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{const element=ref.current;if(!element)return;const preference=window.matchMedia('(prefers-reduced-motion: reduce)');let frame=0;
 const draw=()=>{frame=0;const offset=window.scrollY;const reduced=preference.matches;const progress=reduced?0:Math.min(1,Math.max(0,offset/Math.max(1,document.documentElement.scrollHeight-window.innerHeight)));element.style.setProperty('--glass-progress',String(progress));element.style.setProperty('--glass-x',reduced?'0px':Math.sin(offset/1050)*95+'px');element.style.setProperty('--glass-y',reduced?'0px':Math.min(offset*.08,180)+'px');element.style.setProperty('--glass-turn',reduced?'0deg':Math.sin(offset/1600)*16+'deg')};
 const schedule=()=>{if(!frame)frame=requestAnimationFrame(draw)};const observer=new ResizeObserver(schedule);observer.observe(document.body);window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule);preference.addEventListener('change',schedule);draw();return()=>{cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('scroll',schedule);window.removeEventListener('resize',schedule);preference.removeEventListener('change',schedule)};
 },[]);
 return <div className="ambient-glass" ref={ref} aria-hidden="true"><div className="ambient-orb ambient-orb-blue"/><div className="ambient-orb ambient-orb-violet"/><div className="ambient-orb ambient-orb-teal"/><div className="ambient-grain"/></div>
}
