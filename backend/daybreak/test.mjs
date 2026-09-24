import {render,validateEdition,config} from './render.mjs';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
const now=new Date().toISOString();
const e={date:now.slice(0,10),researchedAt:now,reviewComplete:true,sections:config.sections.map((title,i)=>({title,deck:'Test fixture, not news',stories:Array.from({length:config.sectionRules[title].min},(_,j)=>({eventId:`test-${i}-${j}`,category:'Test',headline:`Fixture story ${i} ${j}`,summary:'Synthetic test only.',publishedAt:now,sources:[{url:`https://source-a-${i}.example/${j}`,label:'Test source A',verifiedAt:now},{url:`https://source-b-${i}.example/${j}`,label:'Test source B',verifiedAt:now}]}))})),metrics:config.metrics.map(label=>({label,value:'Source unavailable',asOf:'Test only',source:'https://example.com/metric'})),marketAnalysis:'Synthetic test, not a market claim.',marketAnalysisSources:[],earnings:{items:[],emptyReason:'Test only'}};
const prices={generatedAt:now,rows:Array.from({length:24},(_,i)=>({symbol:`TEST${i}`,name:'Fixture',exchange:'Test',currency:'USD',price:10+i,week:i<12?i+1:-i,month:-i,asOf:e.date,quoteUrl:`https://example.com/quote/${i}`}))};
const out=await fs.mkdtemp(path.join(os.tmpdir(),'daybreak-test-'));
const result=await render(e,prices,prices,out);
const validation=execFileSync('python3',[new URL('./validate_html.py',import.meta.url).pathname,out,result.archive],{encoding:'utf8'});
assert((await fs.readFile(path.join(out,result.archive))).equals(await fs.readFile(path.join(out,'daybreak-latest.html'))));
const duplicate=structuredClone(e);duplicate.sections[1].stories[0].eventId='test-0-0';assert.throws(()=>validateEdition(duplicate),/Duplicate/);
const badUrl=structuredClone(e);badUrl.sections[0].stories[0].sources[0].url='javascript:alert(1)';assert.throws(()=>validateEdition(badUrl));
// A section below its minimum publishes; the edition is thinner, not refused.
const thin=structuredClone(e);thin.sections[4].stories=[];thin.sections[4].emptyReason='Nothing verified in this search.';validateEdition(thin);
// An empty section still has to say why it is empty.
const silent=structuredClone(e);silent.sections[4].stories=[];delete silent.sections[4].emptyReason;assert.throws(()=>validateEdition(silent),/Explain an empty region/);
// The maximum stays a hard bound.
const over=structuredClone(e);const s0=over.sections[0];const max=config.sectionRules[s0.title].max;
while(s0.stories.length<=max)s0.stories.push({...structuredClone(s0.stories[0]),eventId:`over-${s0.stories.length}`,headline:`Overflow story ${s0.stories.length}`});
assert.throws(()=>validateEdition(over),/allows at most/);
const sparse={...prices,rows:prices.rows.map(x=>({...x,week:-1}))};await render(e,sparse,prices,out);assert((await fs.readFile(path.join(out,result.archive),'utf8')).includes('No additional eligible stock'));
console.log('PASS: render, balanced HTML, section order, table counts, checksums, duplicate rejection, URL rejection, thin-section tolerance, empty-section reason, section maximum and unavailable slots');
console.log(validation.trim());
