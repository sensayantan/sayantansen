import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
export const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const config=JSON.parse(await fs.readFile(new URL('./config.json',import.meta.url)));
const esc=x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const pct=x=>Number.isFinite(x)?`${x>=0?'+':''}${x.toFixed(1)}%`:'Source unavailable';
const tone=x=>Number.isFinite(x)?(x>=0?'up':'down'):'na';
const price=x=>Number.isFinite(x.price)?new Intl.NumberFormat('en-US',{style:'currency',currency:x.currency||'USD'}).format(x.price):'Source unavailable';
const url=x=>{const u=new URL(x);assert.equal(u.protocol,'https:','Only HTTPS sources allowed');return esc(u.href);};
const link=(u,label)=>`<a href="${url(u)}" target="_blank" rel="noopener">${esc(label)} ↗</a>`;
export function validateEdition(e) {
  assert(/^\d{4}-\d{2}-\d{2}$/.test(e.date),'ISO edition date required');
  assert.equal(new Date(e.date+'T12:00:00Z').toISOString().slice(0,10),e.date);
  assert.equal(e.sections.length,config.sections.length);
  const seen=new Set();
  e.sections.forEach((s,i)=>{
    assert.equal(s.title,config.sections[i]);assert(Array.isArray(s.stories));
    if(!s.stories.length)assert(s.emptyReason,'Explain an empty region');
    for(const x of s.stories) {
      assert(x.eventId&&x.headline&&x.summary&&x.publishedAt&&x.sources?.length,'Incomplete story');
      assert(!Number.isNaN(Date.parse(x.publishedAt)),'Invalid publication timestamp');
      assert(x.sources.every(src=>src.verifiedAt&&src.label),'Verified sources required');
      const keys=[`event:${x.eventId}`,`headline:${x.headline.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}`,...x.sources.map(src=>`url:${new URL(src.url).href.replace(/#.*$/,'')}`)];
      for(const key of keys){assert(!seen.has(key),`Duplicate event/headline/source: ${key}`);seen.add(key);}
      x.sources.forEach(src=>url(src.url));
    }
  });
  assert.equal(e.metrics.length,5);
  e.metrics.forEach((m,i)=>{assert.equal(m.label,config.metrics[i]);assert(m.value&&m.asOf&&m.source,'Incomplete market metric');url(m.source);});
  assert(e.researchedAt&&e.marketAnalysis&&e.earnings,'Research timing, analysis and earnings required');
}
export async function render(e,market,portfolio,outputDir) {
  validateEdition(e);
  for(const data of [market,portfolio]){
    assert(data.generatedAt&&data.rows.length,'Missing structured prices');
    for(const row of data.rows)if(!row.error)assert(['price','week','month'].every(key=>Number.isFinite(row[key]))&&row.asOf&&row.quoteUrl,'Incomplete numeric row');
  }
  const verified=market.rows.filter(x=>!x.error);
  const sorted=[...verified].sort((a,b)=>b.week-a.week);
  assert(verified.length>=10,'Insufficient market universe');
  const groups=[sorted.slice(0,5),[...sorted].reverse().slice(0,5),sorted.filter(x=>x.week>0).slice(0,10),[...sorted].reverse().filter(x=>x.week<0).slice(0,10)];
  // Explicit unavailable slots preserve table size without inventing an eligible stock.
  for(let i=2;i<4;i++)while(groups[i].length<10)groups[i].push({symbol:'Source unavailable',error:'No additional eligible stock in the disclosed tracking universe'});
  const rows=data=>data.map(x=>`<tr><td>${x.quoteUrl?link(x.quoteUrl,x.symbol):esc(x.symbol)}<small>${esc(x.name||'')}</small></td><td>${price(x)}<small>${esc(x.exchange||'Source unavailable')} · ${esc(x.asOf||'Source unavailable')}</small></td><td class="${tone(x.week)}">${pct(x.week)}</td><td class="${tone(x.month)}">${pct(x.month)}</td><td>${esc(x.error||x.catalyst||'Catalyst: source unavailable; price movement alone does not establish a cause.')}</td></tr>`).join('');
  const table=(title,data,note)=>`<div class="block"><h3>${esc(title)}<span>${esc(note)}</span></h3><table><thead><tr><th>Company</th><th>Price / exchange / date</th><th>7-day</th><th>1-month</th><th>Catalyst / verification</th></tr></thead><tbody>${rows(data)}</tbody></table></div>`;
  const down=portfolio.rows.filter(x=>!x.error&&x.week<0&&x.month<0).sort((a,b)=>(a.week+a.month)-(b.week+b.month));
  const watch=down.map(x=>({...x,catalyst:`${Math.min(x.week,x.month)<=-5?'Higher review':'Monitor'} — review priority only, not a buy/sell recommendation.`}));
  const unavailable=portfolio.rows.filter(x=>x.error);
  const editorial=e.sections.map((s,i)=>`<section class="section" id="s${i}"><div class="sectionTitle"><p>${esc(s.deck||'')}</p><h2>${esc(s.title)}</h2></div><div class="stories">${s.stories.map((x,j)=>`<article class="story"><span>${String(j+1).padStart(2,'0')}</span><div><small>${esc(x.category)} · ${esc(x.publishedAt.slice(0,10))}</small><h3>${esc(x.headline)}</h3><p>${esc(x.summary)}</p><div class="links">${x.sources.map(src=>link(src.url,src.label)).join(' ')}</div></div></article>`).join('')||`<p>${esc(s.emptyReason)}</p>`}</div></section>`).join('');
  const earnings=e.earnings.items.map(x=>{
    assert(x.title&&x.summary&&x.officialUrl&&x.independentUrl);return `<article class="earning"><h4>${esc(x.title)}</h4><p>${esc(x.summary)}</p><div class="links">${link(x.officialUrl,'Official report')}${link(x.independentUrl,'Independent coverage')}</div></article>`;
  }).join('')||`<p>${esc(e.earnings.emptyReason||'No newly published results verified at the research cutoff.')}</p>`;
  const content=editorial+`<section class="markets" id="markets"><div class="sectionTitle"><p>Verified prices · review before acting</p><h2>Money / Markets</h2></div><div class="snapshot">${esc(e.marketAnalysis)} ${e.marketAnalysisSources.map(x=>link(x,'Source')).join(' ')}</div><div class="pair">${table('Top gainers',groups[0],'Five strongest 7-day moves in the disclosed tracking universe')}${table('Top losers',groups[1],'Five weakest 7-day moves in the same universe')}</div><div class="pair">${table('Large-cap increase',groups[2],'10 positive moves, or explicit unavailable slots')}${table('Large-cap decrease',groups[3],'10 negative moves, or explicit unavailable slots')}</div>${table('Your portfolio trend watch',watch,`${watch.length} holdings declined over both horizons; priority is not investment advice`)}${unavailable.length?table('Portfolio values unavailable',unavailable,'These holdings cannot be classified reliably'):''}<div class="block wide"><h3>S&amp;P 500 earnings newsroom</h3><div class="earnings">${earnings}</div></div><p class="note">Method: unadjusted Yahoo daily-bar prices, compared with the nearest available close on or before 7 and 30 calendar days earlier. Today’s daily bar can be intraday; mutual funds may have an earlier NAV. Splits and distributions can affect unadjusted returns. “Top” refers to the ${market.rows.length}-symbol tracking universe, not the whole exchange. Price data fetched ${esc(market.generatedAt)}; portfolio data fetched ${esc(portfolio.generatedAt)}. General information, not investment advice.</p></section>`;
  const [year,month,day]=e.date.split('-');const mon=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][Number(month)-1];
  const values={DATE_LABEL:`${day}-${mon}-${year.slice(-2)}`,GENERATED_AT:new Date().toISOString(),NAVIGATION:e.sections.map((s,i)=>`<a href="#s${i}">${esc(s.title)}</a>`).join('')+'<a href="#markets">Markets</a>',METRICS:`<div class="indexStrip" aria-label="Market snapshot">${e.metrics.map(m=>`<div class="metric"><small>${esc(m.label)}</small><strong>${esc(m.value)}</strong>${link(m.source,m.asOf)}</div>`).join('')}</div>`,QUALITY:`<div class="quality">Edition research cutoff: ${esc(e.researchedAt)}. Every metric carries its own source date; unavailable values are not estimated.</div>`,CONTENT:content};
  let html=await fs.readFile(new URL('./template.html',import.meta.url),'utf8');html=html.replace(/\{\{([A-Z_]+)\}\}/g,(_,key)=>{assert(key in values,`Unknown template slot ${key}`);return values[key];});
  assert(!html.includes('{{')&&!html.includes('NaN')&&!html.includes('undefined'));
  await fs.mkdir(outputDir,{recursive:true});
  const archive=`daybreak-${year}-${mon}-${day}.html`;
  await Promise.all(['daybreak-latest.html',archive].map(name=>fs.writeFile(path.join(outputDir,name),html)));
  return {archive,dateLabel:values.DATE_LABEL,sha256:crypto.createHash('sha256').update(html).digest('hex'),portfolioDownBoth:down.length};
}
if(process.argv[1]===fileURLToPath(import.meta.url)) {
  const [editionPath,marketPath,portfolioPath,outputDir]=process.argv.slice(2);assert(outputDir,'Usage: node render.mjs EDITION MARKET PORTFOLIO OUTPUT_DIR');
  const data=await Promise.all([editionPath,marketPath,portfolioPath].map(async p=>JSON.parse(await fs.readFile(p))));
  console.log(JSON.stringify(await render(...data,path.resolve(outputDir))));
}
