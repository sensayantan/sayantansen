import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {config,editionDigest,repo,sourceRosters,validateAudit,validateEdition} from './render.mjs';

const [mode,editionArg,auditArg]=process.argv.slice(2);
assert(['init','verify'].includes(mode)&&editionArg&&auditArg,'Usage: node audit.mjs init|verify EDITION_JSON AUDIT_JSON');
const editionPath=path.resolve(editionArg),auditPath=path.resolve(auditArg);
assert(editionPath.startsWith(path.join(repo,'.daybreak-work')+path.sep)&&auditPath.startsWith(path.join(repo,'.daybreak-work')+path.sep),'Edition and audit must stay in .daybreak-work');
const edition=JSON.parse(await fs.readFile(editionPath));validateEdition(edition);
const key=value=>value.toLowerCase().replace(/[^a-z0-9]+/g,'');

if(mode==='init') {
  const audit={date:edition.date,researchedAt:edition.researchedAt,editionSha256:editionDigest(edition),sections:config.sections.map((title,i)=>({
    title,
    sources:sourceRosters.get(key(title)).map(source=>({rosterUrl:source.url,status:'not_retrieved',checkedAt:edition.researchedAt,note:'Not yet audited; update this status after the source is actually checked.',articleUrls:[]})),
    supplementalArticleUrls:edition.sections[i].stories.flatMap(story=>story.sources.map(source=>source.url))
  }))};
  await fs.mkdir(path.dirname(auditPath),{recursive:true});await fs.writeFile(auditPath,JSON.stringify(audit,null,2));
  console.log(`Audit skeleton created at ${auditPath}; publication labels every roster entry not retrieved until the researcher records actual checks.`);
} else {
  const audit=JSON.parse(await fs.readFile(auditPath));validateAudit(audit,edition);console.log('Research audit is current, complete, bound to the edition, and covers every published source URL.');
}
