// Cloud entry point; ticker secret never enters research/model requests or logs.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {repo} from './render.mjs';
const key=process.env.OPENAI_API_KEY,model=process.env.DAYBREAK_OPENAI_MODEL;
assert(key&&model,'Set OPENAI_API_KEY secret and DAYBREAK_OPENAI_MODEL variable');
const tickers=JSON.parse(process.env.DAYBREAK_PORTFOLIO_SYMBOLS||'null');
assert(Array.isArray(tickers)&&tickers.length===96&&new Set(tickers).size===96&&tickers.every(s=>typeof s==='string'&&/^[A-Z][A-Z0-9.-]{0,9}$/.test(s)),'Configure private 96-ticker secret before spending on research');
const work=path.join(repo,'.daybreak-work');await fs.mkdir(work,{recursive:true});
const symbols=path.join(work,'cloud-symbols.json'),edition=path.join(work,'edition.json');
await fs.writeFile(symbols,JSON.stringify(tickers),{mode:0o600});
// Remove ticker secret from the environment of research entirely.
const researchEnv={...process.env};delete researchEnv.DAYBREAK_PORTFOLIO_SYMBOLS;
execFileSync(process.execPath,['backend/daybreak/research.mjs','--output',edition],{cwd:repo,env:researchEnv,stdio:'inherit'});
const publishEnv={...process.env};delete publishEnv.OPENAI_API_KEY;delete publishEnv.DAYBREAK_PORTFOLIO_SYMBOLS;
execFileSync(process.execPath,['backend/daybreak/run.mjs','--edition',edition,'--portfolio-symbols',symbols,'--authorize-yahoo-portfolio',...(process.argv.includes('--publish')?['--publish']:[]),...(process.argv.includes('--defer-pages-verification')?['--defer-pages-verification']:[])],{cwd:repo,env:publishEnv,stdio:'inherit'});
