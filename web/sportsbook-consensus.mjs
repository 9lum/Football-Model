import {decimal} from './market-core.mjs';
// One representative line per book: most balanced two-sided market, median fallback.
export function sportsbookConsensus(quotes,market){
 const books=new Map();for(const q of quotes||[]){if(q.market!==market||!Number.isFinite(q.line)||!q.book)continue;let lines=books.get(q.book);if(!lines){lines=new Map();books.set(q.book,lines)}let row=lines.get(q.line);if(!row){row={line:q.line,quotes:[]};lines.set(q.line,row)}row.quotes.push(q)}
 const selected=[];for(const [book,lines] of books){let candidates=[...lines.values()];const fresh=candidates.filter(r=>r.quotes.some(q=>!(q.flags||[]).includes('stale odds')));if(fresh.length)candidates=fresh;
 const sorted=candidates.map(r=>r.line).sort((a,b)=>a-b),middle=(sorted[Math.floor((sorted.length-1)/2)]+sorted[Math.floor(sorted.length/2)])/2;
 const score=r=>{const over=r.quotes.find(q=>q.side==='Over'),under=r.quotes.find(q=>q.side==='Under');try{if(over&&under){const a=1/decimal(over.price),b=1/decimal(under.price);return Math.abs(a-b)/(a+b)}}catch{}return Infinity};
 candidates.sort((a,b)=>{const x=score(a),y=score(b);return (x===y?0:x-y)||Math.abs(a.line-middle)-Math.abs(b.line-middle)||a.line-b.line});const row=candidates[0];selected.push({book,line:row.line,stale:row.quotes.every(q=>(q.flags||[]).includes('stale odds'))});
 }
 return {mean:selected.length?selected.reduce((s,b)=>s+b.line,0)/selected.length:null,books:selected.length,stale:selected.some(b=>b.stale),allStale:selected.length>0&&selected.every(b=>b.stale),lines:selected};
}
