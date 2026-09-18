// Called after either Codex or research.mjs produces a fresh edition.json.
// No standalone timer, model API calls, or news crawling is hidden in this script.
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {repo,render,validateEdition} from './render.mjs';
const args=process.argv.slice(2);const arg=key=>args[args.indexOf(key)+1];
assert(args.includes('--edition')&&(args.includes('--portfolio')!==args.includes('--portfolio-symbols')),'Required: --edition JSON and exactly one of --portfolio XLSX / --portfolio-symbols PRIVATE_JSON');
assert(args.includes('--authorize-yahoo-portfolio'),'Explicit ticker-only Yahoo authorization flag required');
const e=JSON.parse(await fs.readFile(path.resolve(arg('--edition'))));validateEdition(e);
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Los_Angeles',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
assert.equal(e.date,today,'Refuse stale edition date');
assert.equal(e.reviewComplete,true,'Agent must complete source, significance and event-dedup review');
const fresh=t=>{const age=Date.now()-Date.parse(t);assert(Number.isFinite(age)&&age>=-300000&&age<=24*3600000,'Research/source verification must be within 24 hours');};
fresh(e.researchedAt);
for(const s of e.sections)for(const x of s.stories){x.sources.forEach(src=>fresh(src.verifiedAt));const age=Date.now()-Date.parse(x.publishedAt);assert(age>=-300000,'Future publication time');assert(age<=48*3600000||(x.contextOnly&&x.contextReason),'Stale story without explicit context label');}
const run=(bin,a)=>execFileSync(bin,a,{cwd:repo,encoding:'utf8',stdio:['ignore','pipe','inherit']}).trim();
const publish=args.includes('--publish');
if(publish){assert.equal(run('git',['branch','--show-current']),'main');assert.equal(run('git',['status','--porcelain']),'','Publisher must be clean before publication');run('git',['fetch','origin']);run('git',['merge','--ff-only','origin/main']);}
const work=path.join(repo,'.daybreak-work');await fs.mkdir(work,{recursive:true});
const symbols=path.join(work,'portfolio-symbols.json'),marketFile=path.join(work,'market.json'),portfolioFile=path.join(work,'portfolio.json');
if(args.includes('--portfolio'))run('python3',['backend/daybreak/extract_portfolio.py',path.resolve(arg('--portfolio')),symbols]);
else {
  const data=JSON.parse(await fs.readFile(path.resolve(arg('--portfolio-symbols'))));
  assert(Array.isArray(data)&&data.length===96&&new Set(data).size===96&&data.every(s=>typeof s==='string'&&/^[A-Z][A-Z0-9.-]{0,9}$/.test(s)),'Expected exactly 96 unique ticker symbols only');
  await fs.writeFile(symbols,JSON.stringify(data));
}
run(process.execPath,['backend/daybreak/fetch-prices.mjs','--output',marketFile]);
run(process.execPath,['backend/daybreak/fetch-prices.mjs','--symbols',symbols,'--output',portfolioFile]);
const [market,portfolio]=await Promise.all([marketFile,portfolioFile].map(async p=>JSON.parse(await fs.readFile(p))));
const output=publish?path.join(repo,'DAYBREAK'):path.join(work,'preview');
const manifest=path.join(repo,'DAYBREAK/latest.json');const before=await fs.readFile(manifest);
assert.deepEqual(JSON.parse(before),{file:'daybreak-latest.html'});
const result=await render(e,market,portfolio,output);
console.log(run('python3',['backend/daybreak/validate_html.py',output,result.archive]));
assert(before.equals(await fs.readFile(manifest)),'latest.json changed unexpectedly');
if(publish){
  const files=['DAYBREAK/daybreak-latest.html',`DAYBREAK/${result.archive}`];
  run('git',['add','--',...files]);
  const staged=run('git',['diff','--cached','--name-only']).split('\n').filter(Boolean);
  assert(staged.every(p=>files.includes(p)),'Unrelated staged file; refuse commit');
  if(staged.length){run('git',['commit','-m',`Publish Daybreak for ${e.date}`]);run('git',['push','origin','main']);}
  result.commit=run('git',['rev-parse','--short','HEAD']);
  result.url=`https://sensayantan.github.io/sayantansen/DAYBREAK/daybreak-latest.html?v=${e.date}-${result.commit}`;
  // A pushed commit is not proof of deployment. Check Pages for up to 3 minutes.
  if(args.includes('--defer-pages-verification')) {
    console.log(JSON.stringify({...result,deployed:false,mode:'pushed-awaiting-deployment',output}));
    process.exit(0);
  }
  let deployed=false;
  for(let attempt=0;attempt<12;attempt++){
    try{const res=await fetch(result.url+`-${attempt}`,{cache:'no-store',signal:AbortSignal.timeout(15000)});if(res.ok&&(await res.text()).includes(`<title>Today’s Curated News for Sayantan Sen — ${result.dateLabel}</title>`)){deployed=true;break;}}catch{}
    console.log('GitHub Pages deployment pending');await new Promise(r=>setTimeout(r,15000));
  }
  result.deployed=deployed;if(!deployed){console.log(JSON.stringify(result));throw Error('Commit pushed, but Pages deployment not yet verified; do not report live success');}
}
console.log(JSON.stringify({...result,mode:publish?'published':'preview',output}));
