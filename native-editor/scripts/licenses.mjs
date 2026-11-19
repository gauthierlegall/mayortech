import {readFile, readdir, writeFile, mkdir, cp} from 'node:fs/promises';
import {resolve, dirname, sep} from 'node:path';
import {createHash} from 'node:crypto';
const root = resolve(import.meta.dirname, '..');
const lock = JSON.parse(await readFile(resolve(root, 'package-lock.json'), 'utf8'));
const packages = [];
const notices = ['Third-party npm packages used by Travaux native editor. Generated from package-lock.json and installed license files.\n'];
for (const [path, entry] of Object.entries(lock.packages)) {
  if (!path || !path.startsWith('node_modules/')) continue;
  let metadata;
  try { metadata = JSON.parse(await readFile(resolve(root, path, 'package.json'), 'utf8')); } catch { continue; }
  const files = (await readdir(resolve(root, path))).filter(name => /^(licen[sc]e|copying|notice)(\.|$)/i.test(name));
  const texts = [];
  for (const file of files) { try { texts.push({file, text: await readFile(resolve(root, path, file), 'utf8')}); } catch {} }
  const combined = texts.map(item => item.text).join('\n');
  const declared = metadata.license ?? metadata.licenses?.map(license => license.type).join(' OR ');
  const inferred = /Mozilla Public License Version 2\.0/.test(combined) ? 'MPL-2.0' : /Permission is hereby granted, free of charge/.test(combined) ? 'MIT' : null;
  const item = {name: metadata.name, version: metadata.version, license: declared ?? inferred, licenseEvidence: declared ? 'package metadata' : 'included license text', integrity: entry.integrity, dev: Boolean(entry.dev), path};
  packages.push(item);
  notices.push(`\n===== ${item.name}@${item.version} | ${JSON.stringify(item.license)} =====\n`);
  for (const {file, text} of texts) notices.push(`\n--- ${file} ---\n${text}\n`);
  if (!files.length) notices.push('No license text included in this npm package; consult upstream.\n');
}
notices.push(`\n===== AFFiNE/BlockSuite MIT notice =====\n${await readFile(resolve(root, 'licenses/BlockSuite-MIT.txt'), 'utf8')}\n`);
// The published theme embeds the preferred TypeScript sources in sourcemaps.
// Extract those exact unmodified files instead of substituting a moving HEAD.
const theme = resolve(root, 'node_modules/@toeverything/theme');
const target = resolve(root, 'vendor-source/theme-1.1.23');
await mkdir(target, {recursive: true});
const sourceEvidence = [];
for (const mapPath of ['dist/index.js.map', 'dist/index.cjs.map', 'dist/v2/index.js.map', 'dist/v2/index.cjs.map']) {
  const map = JSON.parse(await readFile(resolve(theme, mapPath), 'utf8'));
  for (let i = 0; i < map.sources.length; i++) {
    const relative = map.sources[i].replace(/^(\.\.\/)+/, '');
    const content = map.sourcesContent?.[i];
    if (!relative.startsWith('src/') || typeof content !== 'string') throw new Error('theme_source_missing_or_invalid');
    const filename = resolve(target, relative);
    if (!filename.startsWith(target + sep)) throw new Error('theme_source_path_invalid');
    await mkdir(dirname(filename), {recursive: true}); await writeFile(filename, content);
    sourceEvidence.push({source: relative, sourcemap: mapPath, sha256: createHash('sha256').update(content).digest('hex')});
  }
}
await cp(resolve(theme, 'LICENSE'), resolve(target, 'LICENSE'));
await cp(resolve(theme, 'package.json'), resolve(target, 'package.json'));
await writeFile(resolve(target, 'provenance.json'), JSON.stringify({package: '@toeverything/theme', version: '1.1.23', modified: false, tarball: 'https://registry.npmjs.org/@toeverything/theme/-/theme-1.1.23.tgz', sources: sourceEvidence}, null, 2));
await writeFile(resolve(root, 'third-party-licenses.json'), JSON.stringify({lockfileVersion: lock.lockfileVersion, packages}, null, 2) + '\n');
await writeFile(resolve(root, 'THIRD_PARTY_LICENSES.txt'), notices.join(''));
if (process.argv.includes('--dist')) {
  await cp(target, resolve(root, 'dist/vendor-source/theme-1.1.23'), {recursive: true});
  await cp(resolve(root, 'THIRD_PARTY_LICENSES.txt'), resolve(root, 'dist/THIRD_PARTY_LICENSES.txt'));
  await cp(resolve(root, 'third-party-licenses.json'), resolve(root, 'dist/third-party-licenses.json'));
}
console.log(`Recorded ${packages.length} installed package versions/licenses.`);
