// MIT-compatible local backport; upstream attribution and limits are in patches/README.md.
import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(await readFile(path.join(root, 'patches/zod-3.25.76-size-gate.json'), 'utf8'));
const vendor = path.join(root, 'node_modules', 'zod');
const metadata = JSON.parse(await readFile(path.join(vendor, 'package.json'), 'utf8'));
if (metadata.version !== manifest.version) throw new Error('Security patch requires a reviewed Zod version');
const hash = data => createHash('sha256').update(data).digest('hex');
const staged = [];
for (const file of manifest.files) {
  const target = path.resolve(vendor, file.path);
  if (!target.startsWith(vendor + path.sep)) throw new Error('Security patch target outside Zod');
  const current = await readFile(target);
  if (hash(current) === file.after) continue;
  if (hash(current) !== file.before) throw new Error('Unexpected vendor contents; refuse to apply the security patch');
  let content = current;
  for (const operation of [...file.operations].sort((a,b) => b.offset-a.offset)) {
    content = Buffer.concat([content.subarray(0, operation.offset), Buffer.from(operation.insert), content.subarray(operation.offset)]);
  }
  if (hash(content) !== file.after) throw new Error('Security patch digest mismatch');
  staged.push({target,content});
}
for (const item of staged) await writeFile(item.target, item.content);
console.log(`Zod constrained-collection backport verified (${staged.length} files updated).`);
