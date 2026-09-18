import {test} from 'node:test';
import assert from 'node:assert/strict';
import {canonical,sourceUrls,checkSources,rankAndDeduplicate,createClient,pacificDate,research} from './research.mjs';
import {config} from './render.mjs';
const stamp='2026-09-18T17:00:00.000Z';
const card=(i,overrides={})=>({eventId:`e${i}`,headline:`Distinct story number ${i}`,summary:'Verified synthetic evidence.',evidence:'Verified synthetic evidence.',publishedAt:stamp,humanImpact:1,significance:1,sources:[{url:`https://example.com/${i}`,label:'Fixture'}],section:config.sections[i%8],...overrides});
test('source provenance rejects invented URLs, ignores model-written URLs',()=>{
  const r={output:[{type:'web_search_call',action:{sources:[{url:'https://example.com/a?utm_source=x'}]}},{type:'message',content:[{text:'https://invented.com',annotations:[]}]}]};
  const urls=sourceUrls(r);assert.equal(urls.size,1);checkSources(['https://example.com/a'],urls);
  assert.throws(()=>checkSources(['https://invented.com'],urls));
  assert.equal(canonical('https://example.com/a#b'),'https://example.com/a');assert.throws(()=>canonical('http://example.com'));
});
test('rank promotes major harm and removes stale, future and duplicate events',()=>{
  const c=card(1,{headline:'Deadly earthquake damages coastal towns',humanImpact:5});
  const result=rankAndDeduplicate([card(2,{eventId:'e1'}),c,card(3,{publishedAt:'2026-09-01'}),card(4,{publishedAt:'2026-10-01'})],Date.parse(stamp));
  assert.equal(result.length,1);assert.equal(result[0].section,'Top News');assert.equal(result[0].humanImpact,5);
});
test('request budget, credentials and API failures stop without retries',async()=>{
  assert.throws(()=>createClient({model:'fixture'}));assert.throws(()=>createClient({key:'fixture'}));
  let calls=0;
  const request=createClient({key:'fixture',model:'fixture',maxCalls:1,fetchImpl:async()=>{calls++;return {ok:true,json:async()=>({status:'completed',output:[{type:'message',content:[{type:'output_text',text:'{}'}]}]})};}});
  await request({});await assert.rejects(request({}),/budget/);assert.equal(calls,1);
  const fail=createClient({key:'fixture',model:'fixture',fetchImpl:async()=>({ok:false,status:429})});await assert.rejects(fail({}),/no retry/);
});
test('Pacific date respects UTC rollover',()=>assert.equal(pacificDate(new Date('2026-09-19T01:00:00Z')),'2026-09-18'));
test('full research contract uses 20 mocked calls and emits eight sections',async()=>{
  let calls=0,desk=0;
  const request=async body=>{
    calls++;
    if(body.tools)return {status:'completed',output:[{type:'web_search_call',action:{sources:[{url:`https://example.com/${desk}`}]}},{type:'message',content:[{type:'output_text',text:'Synthetic evidence only.'}]}]};
    let data;
    if(desk<8)data={stories:[card(desk,{headline:['Coastal earthquake recovery','Congress passes tax changes','Japan central bank decision','Gulf maritime talks','European energy security','Brazil infrastructure plans','Kenya election court hearing','New semiconductor architecture'][desk]})],emptyReason:''};
    else if(desk===8)data={metrics:config.metrics.map(label=>({label,value:'Source unavailable',asOf:'Fixture only',source:'https://example.com/8'})),marketAnalysis:'Fixture analysis.',marketAnalysisSources:['https://example.com/8']};
    else data={items:[],emptyReason:'No verified new results in fixture; not exhaustive.'};
    desk++;return {status:'completed',output:[{type:'message',content:[{type:'output_text',text:JSON.stringify(data)}]}]};
  };
  const result=await research({request,date:'2026-09-18',now:()=>new Date(stamp)});
  assert.equal(calls,20);assert.equal(result.edition.sections.length,8);assert.equal(result.audit.length,10);
  assert.equal(result.edition.sections[0].stories[0].sources[0].verifiedAt,stamp);
});
