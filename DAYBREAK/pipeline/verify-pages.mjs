import fs from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const html=await fs.readFile('DAYBREAK/daybreak-latest.html','utf8');
const title=html.match(/<title>([^<]+)<\/title>/)?.[0];assert(title,'Missing edition title');
const commit=execFileSync('git',['rev-parse','--short','HEAD'],{encoding:'utf8'}).trim();
const url=`https://sensayantan.github.io/sayantansen/DAYBREAK/daybreak-latest.html?v=${commit}`;
for(let i=0;i<12;i++) {
  try {
    const r=await fetch(`${url}-${i}`,{cache:'no-store',signal:AbortSignal.timeout(15000)});
    if(r.ok&&(await r.text()).includes(title)){console.log(`Verified deployed edition: ${url}`);process.exit(0);}
  }catch{}
  await new Promise(resolve=>setTimeout(resolve,15000));
}
throw Error('HTML pushed, but live edition not verified. Check GitHub Pages deployment.');
