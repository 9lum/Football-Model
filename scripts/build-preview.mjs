import {readFile,writeFile} from 'node:fs/promises';
const template=await readFile('web/research.template.html','utf8');
const core=(await readFile('web/market-core.mjs','utf8')).replace(/^export /gm,'');
const html=template.replace('/* MARKET_CORE */',()=>core);
await writeFile('site-preview.html',html);
console.log('Built standalone site-preview.html');
