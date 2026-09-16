import fs from 'node:fs/promises';
import path from 'node:path';
const args=process.argv.slice(2);
const get=(key)=>args[args.indexOf(key)+1];
if (!args.includes('--output')) throw Error('Required: --output FILE [--symbols PRIVATE_JSON]');
const config=JSON.parse(await fs.readFile(new URL('./config.json',import.meta.url)));
const input=args.includes('--symbols') ? JSON.parse(await fs.readFile(get('--symbols'))) : config.marketSymbols.map(symbol=>({symbol}));
const symbols=[...new Set(input.map(x=>typeof x==='string'?x:x.symbol))];
if (!symbols.length || symbols.some(s=>!/^([A-Z][A-Z0-9.-]{0,9})$/.test(s))) throw Error('Invalid symbol list');
const aliases={BRKB:'BRK-B'};
function prior(points,seconds) {
  const p=points.filter(x=>x.time<=seconds).at(-1);
  if (!p) throw Error('Insufficient historical coverage');
  return p.close;
}
const rows=[];
for(const symbol of symbols) {
  const querySymbol=aliases[symbol]||symbol;
  try {
    const res=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(querySymbol)}?range=3mo&interval=1d&events=history`,{headers:{'user-agent':'Mozilla/5.0 Daybreak/2.0'},signal:AbortSignal.timeout(30000)});
    if(!res.ok) throw Error(`HTTP ${res.status}`);
    const result=(await res.json()).chart?.result?.[0];
    if(!result) throw Error('Source unavailable: no chart result');
    const closes=result.indicators?.quote?.[0]?.close||[];
    const points=(result.timestamp||[]).map((time,i)=>({time,close:closes[i]})).filter(x=>Number.isFinite(x.close)&&x.close>0);
    const latest=points.at(-1); if(!latest) throw Error('No finite price');
    rows.push({symbol,querySymbol,name:result.meta?.longName||result.meta?.shortName||symbol,exchange:result.meta?.fullExchangeName||result.meta?.exchangeName||'Source unavailable',currency:result.meta?.currency||'USD',price:latest.close,week:(latest.close/prior(points,latest.time-7*86400)-1)*100,month:(latest.close/prior(points,latest.time-30*86400)-1)*100,asOf:new Date(latest.time*1000).toISOString().slice(0,10),quoteUrl:`https://finance.yahoo.com/quote/${encodeURIComponent(querySymbol)}/`});
  } catch(e) {rows.push({symbol,error:String(e.message),quoteUrl:`https://finance.yahoo.com/quote/${encodeURIComponent(querySymbol)}/`});}
}
const out=path.resolve(get('--output'));await fs.mkdir(path.dirname(out),{recursive:true});
await fs.writeFile(out,JSON.stringify({generatedAt:new Date().toISOString(),rows},null,2));
console.log(JSON.stringify({total:rows.length,verified:rows.filter(x=>!x.error).length,unavailable:rows.filter(x=>x.error).length}));
