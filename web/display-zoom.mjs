export const ZOOM_STORAGE_KEY='pns-zoom';
export function normalizeZoom(value){const n=Number(value);return Number.isFinite(n)?Math.min(200,Math.max(100,Math.round(n))):100}
export function zoomStyle(value){const zoom=normalizeZoom(value)/100;return {scale:String(zoom),height:(100/zoom)+'vh'}}
// Apply the stored scale before paint; storage can be unavailable in private contexts.
export const zoomBootstrap="try{var z=Number(localStorage.getItem('pns-zoom'));z=Number.isFinite(z)?Math.min(200,Math.max(100,Math.round(z))):100;document.documentElement.style.setProperty('--pns-zoom',String(z/100));document.documentElement.style.setProperty('--pns-viewport-height',String(100/(z/100))+'vh')}catch(e){}";
