import {readFile,writeFile} from 'node:fs/promises';
let html=await readFile('web/research.template.html','utf8');
for(const [marker,file] of [['/* MARKET_CORE */','web/market-core.mjs'],['/* VIEW_MODEL */','web/view-model.mjs']]){
 let source=(await readFile(file,'utf8')).replace(/^import .*;\n/gm,'').replace(/^export /gm,'');html=html.replace(marker,()=>source);
}
await writeFile('site-preview.html',html);console.log('Built standalone site-preview.html');
