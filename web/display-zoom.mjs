export const ZOOM_STORAGE_KEY='pns-zoom';
export const ZOOM_LEVELS=[0,25,50,75,100,125,150,175,200];
// Zero resets to normal size so the navigation can never disappear.
export function normalizeZoom(value){const n=Number(value);return Number.isFinite(n)&&n>0?Math.min(200,Math.max(25,Math.round(n/25)*25)):100}
export function zoomStyle(value){const zoom=normalizeZoom(value)/100;return {scale:String(zoom),height:(100/zoom)+'vh'}}
// Use the same normalization before paint and after hydration.
export const zoomBootstrap=`(()=>{try{const z=(${normalizeZoom.toString()})(localStorage.getItem('pns-zoom'));document.documentElement.style.setProperty('--pns-zoom',String(z/100));document.documentElement.style.setProperty('--pns-viewport-height',String(100/(z/100))+'vh')}catch(e){}})()`;
