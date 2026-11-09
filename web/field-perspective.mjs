// A camera above the near end zone; project world coordinates before drawing SVG.
export function fieldPoint(x,z,depth=true,yaw=0){
 if(!depth)return {x:80+x*5.6,y:410-z*5};
 const scale=1/(1+z/58);
 return {x:360+(x-50)*5.6*scale+yaw*z*.16*scale,y:410-z*10.6*scale};
}
export function fieldPolygon(x0,z0,x1,z1,depth=true,yaw=0){
 return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]].map(([x,z])=>{const p=fieldPoint(x,z,depth,yaw);return `${p.x.toFixed(2)},${p.y.toFixed(2)}`}).join(' ');
}
export const fieldBands={short:[8,18],intermediate:[18,28],deep:[28,58]};
