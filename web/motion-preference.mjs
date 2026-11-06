export const MOTION_PREFERENCE_KEY='pns-background-motion-v2';
export function motionStorage(){try{return globalThis.localStorage||null}catch{return null}}
export function readMotionPreference(storage=motionStorage()){try{return storage?.getItem(MOTION_PREFERENCE_KEY)!=='off'}catch{return true}}
export function applyMotionPreference(root,enabled,storage=motionStorage(),persist=true){root.dataset.backgroundMotion=enabled?'on':'off';if(persist)try{storage?.setItem(MOTION_PREFERENCE_KEY,enabled?'on':'off')}catch{}return enabled}
export function initializeMotionPreference(root,storage=motionStorage()){return applyMotionPreference(root,readMotionPreference(storage),storage,false)}
