import {test} from 'node:test';
import assert from 'node:assert/strict';
import {canonical,sourceUrls,checkSources,rankAndDeduplicate,createClient,pacificDate,research} from './research.mjs';
import {config} from './render.mjs';
const stamp='2026-09-18T17:00:00.000Z';
const card=(i,overrides={})=>({eventId:`e${i}`,headline:`Distinct story number ${i}`,summary:'Verified synthetic evidence.',evidence:'Verified synthetic evidence.',publishedAt:stamp,humanImpact:1,significance:1,sources:[{url:`https://example.com/${i}`,label:'Fixture A'},{url:`https://example.net/${i}`,label:'Fixture B'}],section:config.sections[i%config.sections.length],...overrides});
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
test('full research contract uses 24 mocked calls and emits every configured section',async()=>{
  let calls=0,desk=0,firstResearchPrompt='';
  const request=async body=>{
    calls++;
    if(body.tools) {
      if(!firstResearchPrompt)firstResearchPrompt=body.input;
      const count=desk<config.sections.length?config.sectionRules[config.sections[desk]].target:1;
      const sources=Array.from({length:count},(_,i)=>[{url:`https://example.com/${desk}-${i}`},{url:`https://example.net/${desk}-${i}`}]).flat();
      if(desk>=config.sections.length)sources.push({url:`https://example.com/${desk}`});
      return {status:'completed',output:[{type:'web_search_call',action:{sources}},{type:'message',content:[{type:'output_text',text:'Synthetic evidence only.'}]}]};
    }
    let data;
    if(desk<config.sections.length) {
      const count=config.sectionRules[config.sections[desk]].target;
      data={stories:Array.from({length:count},(_,i)=>card(`${desk}-${i}`,{section:config.sections[desk],headline:`fixturetopic${desk}item${i} uniqueevent${desk}case${i}`})),emptyReason:''};
    }
    else if(desk===config.sections.length)data={metrics:config.metrics.map(label=>({label,value:'Source unavailable',asOf:'Fixture only',source:`https://example.com/${desk}`})),marketAnalysis:'Fixture analysis.',marketAnalysisSources:[`https://example.com/${desk}`]};
    else data={items:[],emptyReason:'No verified new results in fixture; not exhaustive.'};
    desk++;return {status:'completed',output:[{type:'message',content:[{type:'output_text',text:JSON.stringify(data)}]}]};
  };
  const result=await research({request,date:'2026-09-18',now:()=>new Date(stamp),previousStories:[{section:'Top News',eventId:'prior-event',headline:'Prior developing event',summary:'Prior summary',publishedAt:'2026-09-17T17:00:00Z'}]});
  assert.equal(calls,24);assert.equal(result.edition.sections.length,config.sections.length);assert.equal(result.audit.length,config.sections.length+2);
  assert.match(firstResearchPrompt,/Prior developing event/);assert.match(firstResearchPrompt,/material new development/);
  assert.match(firstResearchPrompt,/BBC News/);assert.match(firstResearchPrompt,/Required source roster/);
  assert.equal(result.edition.sections[0].stories[0].sources[0].verifiedAt,stamp);
});
