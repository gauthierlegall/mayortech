import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {databaseViewInitTemplate} from '../vendor/affine/database-view-init.ts';

test('executed vendor function matches its attributed upstream excerpt', async () => {
  const manifest = JSON.parse(await readFile(new URL('../vendor/affine/provenance.json', import.meta.url), 'utf8'));
  const source = await readFile(new URL('../vendor/affine/database-view-init.ts', import.meta.url), 'utf8');
  const fragment = source.match(/export const databaseViewInitTemplate = \([\s\S]*?\n\};/)[0];
  assert.equal(createHash('sha256').update(fragment).digest('hex'), manifest.extracted_function_sha256);
  assert.equal(manifest.commit, '9c615502796516da5d0ff91bed1597b1476c7978');
});

test('upstream initializer makes three real row operations before creating its view', () => {
  const events = [];
  databaseViewInitTemplate({rowAdd: position => events.push(['row', position]), viewManager: {viewAdd: type => events.push(['view', type])}}, 'table');
  assert.deepEqual(events, [['row', 'end'], ['row', 'end'], ['row', 'end'], ['view', 'table']]);
});
