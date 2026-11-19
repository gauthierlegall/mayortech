import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {z} from 'zod';
const require = createRequire(import.meta.url);

for (const [mode, library] of [['esm', z], ['commonjs', require('zod').z]]) {
  test(`${mode}: oversized bounded arrays reject before parsing each member`, () => {
    let visited = 0;
    const member = library.string().superRefine(() => { visited += 1; });
    const result = library.array(member).max(2).safeParse(['a', 'b', 'c']);
    assert.equal(result.success, false);
    assert.equal(visited, 0);
    assert.equal(result.error.issues.length, 1);
    assert.equal(result.error.issues[0].code, 'too_big');
  });
  test(`${mode}: exact length rejects oversized arrays without walking them`, async () => {
    let visited = 0;
    const member = library.string().superRefine(async () => { visited += 1; });
    assert.equal((await library.array(member).length(2).safeParseAsync(['a', 'b', 'c'])).success, false);
    assert.equal(visited, 0);
  });
  test(`${mode}: bounded sets reject before parsing elements`, () => {
    let visited = 0;
    const member = library.string().superRefine(() => { visited += 1; });
    assert.equal(library.set(member).max(2).safeParse(new Set(['a','b','c'])).success, false);
    assert.equal(visited, 0);
  });
  test(`${mode}: valid bounded collections preserve values and legacy function API`, () => {
    assert.deepEqual(library.array(library.string()).max(2).parse(['a','b']), ['a','b']);
    assert.equal(library.set(library.string()).max(2).parse(new Set(['a'])).size, 1);
    assert.equal(library.function().args(library.string()).returns(library.string()).implement(value => value)('a'), 'a');
  });
}
